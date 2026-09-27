"""Explicit, offline pixel comparison. Metrics are not semantic design acceptance."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from project_history_journal import redact_secrets

MAX_PIXELS = 16_000_000
MAX_BYTES = 32 * 1024 * 1024


def _metadata(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError('metadata must be an object')
    for field in ('source_uri', 'captured_at', 'scene_id'):
        if not isinstance(value.get(field), str) or not value[field].strip():
            raise ValueError(f'{field} is required')
    try:
        stamp = datetime.fromisoformat(value['captured_at'].replace('Z', '+00:00'))
        if stamp.utcoffset() is None:
            raise ValueError('timezone required')
    except (TypeError, ValueError) as exc:
        raise ValueError('captured_at must be an ISO timestamp with timezone') from exc
    viewport = value.get('viewport')
    if not isinstance(viewport, dict):
        raise ValueError('viewport is required')
    for field in ('width', 'height'):
        if type(viewport.get(field)) is not int or viewport[field] <= 0:
            raise ValueError('viewport width and height must be positive integers')
    if 'device_scale_factor' in viewport:
        dpr = viewport['device_scale_factor']
        if isinstance(dpr, bool) or not isinstance(dpr, (int, float)) or not math.isfinite(dpr) or dpr <= 0:
            raise ValueError('device_scale_factor must be positive and finite')
    result = {key: value[key] for key in ('source_uri', 'captured_at', 'scene_id', 'viewport')}
    if 'claimed_sha' in value:
        if not isinstance(value['claimed_sha'], str) or not value['claimed_sha'].strip():
            raise ValueError('claimed_sha must be a nonempty string')
        result['claimed_sha'] = value['claimed_sha']
    return redact_secrets(result)


def _load(path: Path):
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError('Install requirements-visual.txt to compare images') from exc
    with path.open('rb') as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError('image exceeds byte limit')
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            opened = Image.open(io.BytesIO(data))
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError('image exceeds decoder safety limit') from exc
    with opened as image:
        if image.format not in ('PNG', 'JPEG', 'WEBP'):
            raise ValueError('only PNG, JPEG and WEBP are supported')
        if image.width * image.height > MAX_PIXELS:
            raise ValueError('image exceeds pixel limit')
        if getattr(image, 'n_frames', 1) != 1:
            raise ValueError('animated images cannot represent a single scene')
        if image.getexif().get(274, 1) != 1:
            raise ValueError('normalize EXIF orientation explicitly before comparison')
        rgba = image.convert('RGBA')
    return rgba, hashlib.sha256(data).hexdigest(), len(data)


def compare_images(reference: str | Path, current: str | Path, *,
                   reference_metadata: dict[str, Any], current_metadata: dict[str, Any],
                   channel_threshold: int, allowed_changed_ratio: float,
                   difference: str | Path | None = None) -> dict[str, Any]:
    """Require caller-selected thresholds. Never infer a commit or fetch a source URI."""
    if type(channel_threshold) is not int or not 0 <= channel_threshold <= 255:
        raise ValueError('channel_threshold must be an integer from 0 to 255')
    if isinstance(allowed_changed_ratio, bool) or not isinstance(allowed_changed_ratio, (int, float)) or not math.isfinite(allowed_changed_ratio) or not 0 <= allowed_changed_ratio <= 1:
        raise ValueError('allowed_changed_ratio must be finite from 0 to 1')
    ref_meta, cur_meta = _metadata(reference_metadata), _metadata(current_metadata)
    # Compare original identifiers before redaction can collapse distinct values.
    for field in ('scene_id', 'viewport'):
        if reference_metadata[field] != current_metadata[field]:
            raise ValueError(f'comparison rejected: {field} mismatch')
    ref_path, cur_path = Path(reference).resolve(), Path(current).resolve()
    out = Path(difference).absolute() if difference is not None else None
    if out is not None and (out.resolve() in (ref_path, cur_path) or out.exists() or out.is_symlink()):
        raise ValueError('difference output must be a new file distinct from inputs')
    ref, ref_hash, ref_bytes = _load(ref_path)
    cur, cur_hash, cur_bytes = _load(cur_path)
    if ref.size != cur.size:
        raise ValueError('comparison rejected: image dimensions mismatch; no rescaling performed')
    from PIL import ImageChops
    delta = ImageChops.difference(ref, cur)
    channels = delta.split()
    maximum = channels[0]
    for channel in channels[1:]:
        maximum = ImageChops.lighter(maximum, channel)
    hist = maximum.histogram()
    changed = sum(hist[channel_threshold + 1:])
    total = ref.width * ref.height
    ratio = changed / total
    mean = [sum(level * count for level, count in enumerate(channel.histogram())) / total for channel in channels]
    output = None
    if out is not None:
        # RGB grayscale magnitude also shows alpha-only changes; no transparent diff.
        buffer = io.BytesIO()
        maximum.convert('RGB').save(buffer, format='PNG')
        payload = buffer.getvalue()
        with out.open('xb') as stream:
            stream.write(payload)
        output = {'path': redact_secrets(str(out)), 'sha256': hashlib.sha256(payload).hexdigest(),
                  'representation': 'max absolute RGBA channel difference, grayscale'}
    def evidence(path, meta, digest, size):
        return {'path': redact_secrets(str(path)), 'metadata': meta,
                'metadata_evidence_class': 'reported', 'sha256': digest, 'bytes': size,
                'file_evidence_class': 'observed'}
    return {'schema': 'terminal-visual-comparison/v1',
            'compared_at': datetime.now(timezone.utc).isoformat(),
            'reference': evidence(ref_path, ref_meta, ref_hash, ref_bytes),
            'current': evidence(cur_path, cur_meta, cur_hash, cur_bytes),
            'width': ref.width, 'height': ref.height, 'channels': 'RGBA',
            'channel_threshold': channel_threshold, 'allowed_changed_ratio': allowed_changed_ratio,
            'changed_pixels': changed, 'total_pixels': total, 'changed_ratio': ratio,
            'mean_absolute_channel_difference': mean,
            'pixel_gate': 'PASS' if ratio <= allowed_changed_ratio else 'FAIL',
            'semantic_acceptance': 'NOT_RUN', 'capture_provenance': 'reported_unverified',
            'difference': output,
            'limitations': ['No browser capture performed', 'No commit or build identity verified',
                            'Pixel similarity does not prove usability or design acceptance']}


def main(argv=None) -> int:
    # Receipts are UTF-8 even when Windows inherits a legacy console encoding.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='strict')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True)
    parser.add_argument('--current', required=True)
    parser.add_argument('--reference-metadata', required=True)
    parser.add_argument('--current-metadata', required=True)
    parser.add_argument('--channel-threshold', required=True, type=int)
    parser.add_argument('--allowed-changed-ratio', required=True, type=float)
    parser.add_argument('--difference')
    args = parser.parse_args(argv)
    try:
        receipt = compare_images(args.reference, args.current,
            reference_metadata=json.loads(Path(args.reference_metadata).read_text(encoding='utf-8')),
            current_metadata=json.loads(Path(args.current_metadata).read_text(encoding='utf-8')),
            channel_threshold=args.channel_threshold, allowed_changed_ratio=args.allowed_changed_ratio,
            difference=args.difference)
    except (ValueError, OSError, RuntimeError) as exc:
        print(json.dumps({'status': 'REJECTED', 'error': redact_secrets(str(exc))}, ensure_ascii=False))
        return 2
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
    return 0 if receipt['pixel_gate'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
