import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from terminal_visual import compare_images


class VisualTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.ref = self.root / 'эталон.png'
        self.cur = self.root / 'текущий.png'
        Image.new('RGBA', (4, 4), (10, 20, 30, 255)).save(self.ref)
        Image.new('RGBA', (4, 4), (10, 20, 30, 255)).save(self.cur)
        self.meta = {'source_uri': 'https://example.test/экран', 'captured_at': '2026-09-24T00:00:00Z',
                     'scene_id': 'главная', 'viewport': {'width': 4, 'height': 4}, 'claimed_sha': 'abc123'}

    def compare(self, **kwargs):
        options = dict(reference_metadata=self.meta, current_metadata=copy.deepcopy(self.meta),
                       channel_threshold=0, allowed_changed_ratio=0)
        options.update(kwargs)
        return compare_images(self.ref, self.cur, **options)

    def test_identical_not_semantic_acceptance(self):
        result = self.compare()
        self.assertEqual(result['pixel_gate'], 'PASS')
        self.assertEqual(result['semantic_acceptance'], 'NOT_RUN')
        self.assertEqual(result['changed_pixels'], 0)
        self.assertNotIn('verified_version', result)
        self.assertEqual(result['current']['metadata_evidence_class'], 'reported')
        self.assertEqual(result['current']['metadata']['claimed_sha'], 'abc123')

    def test_single_pixel_and_diff(self):
        with Image.open(self.cur) as im:
            im.putpixel((1, 1), (11, 20, 30, 255))
            im.save(self.cur)
        out = self.root / 'разница.png'
        result = self.compare(difference=out)
        self.assertEqual(result['changed_pixels'], 1)
        self.assertEqual(result['changed_ratio'], 1 / 16)
        self.assertEqual(result['pixel_gate'], 'FAIL')
        with Image.open(out) as im:
            self.assertEqual(im.getpixel((1, 1)), (1, 1, 1))
        self.assertEqual(self.compare(channel_threshold=1)['pixel_gate'], 'PASS')
        self.assertEqual(self.compare(allowed_changed_ratio=1/16)['pixel_gate'], 'PASS')

    def test_cli_forces_utf8_with_legacy_stdio_encoding(self):
        meta = self.root / 'метаданные.json'
        meta.write_text(json.dumps(self.meta, ensure_ascii=False), encoding='utf-8')
        result = subprocess.run(
            [sys.executable, str(Path(__file__).resolve().parents[1] / 'terminal_visual.py'),
             '--reference', str(self.ref), '--current', str(self.cur),
             '--reference-metadata', str(meta), '--current-metadata', str(meta),
             '--channel-threshold', '0', '--allowed-changed-ratio', '0'],
            env={**os.environ, 'PYTHONIOENCODING': 'cp1252'}, capture_output=True,
            timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
        receipt = json.loads(result.stdout.decode('utf-8'))
        self.assertEqual(receipt['reference']['metadata']['scene_id'], 'главная')
        self.assertTrue(receipt['current']['path'].endswith('текущий.png'))

    def test_alpha_only_detected(self):
        Image.new('RGBA', (4, 4), (10, 20, 30, 254)).save(self.cur)
        self.assertEqual(self.compare()['changed_pixels'], 16)

    def test_scene_and_viewport_mismatch(self):
        for field, value in [('scene_id', 'other'), ('viewport', {'width': 5, 'height': 4})]:
            meta = copy.deepcopy(self.meta)
            meta[field] = value
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                self.compare(current_metadata=meta)

    def test_dimension_mismatch(self):
        Image.new('RGB', (5, 4)).save(self.cur)
        with self.assertRaisesRegex(ValueError, 'dimensions mismatch'):
            self.compare()

    def test_invalid_provenance(self):
        for field, value in [('captured_at', '2026-09-24'), ('source_uri', ''), ('scene_id', '')]:
            meta = copy.deepcopy(self.meta)
            meta[field] = value
            with self.assertRaises(ValueError):
                self.compare(current_metadata=meta)

    def test_invalid_thresholds(self):
        for value in [-1, 256, True, 0.5]:
            with self.assertRaises(ValueError):
                self.compare(channel_threshold=value)
        for value in [float('nan'), float('inf'), -1, 2, True]:
            with self.assertRaises(ValueError):
                self.compare(allowed_changed_ratio=value)

    def test_no_input_or_existing_output_overwrite(self):
        original = self.ref.read_bytes()
        for path in [self.ref, self.cur]:
            with self.assertRaises(ValueError):
                self.compare(difference=path)
        self.assertEqual(self.ref.read_bytes(), original)

    def test_pixel_and_byte_limits(self):
        with patch('terminal_visual.MAX_PIXELS', 15):
            with self.assertRaisesRegex(ValueError, 'pixel limit'):
                self.compare()
        with patch('terminal_visual.MAX_BYTES', 5):
            with self.assertRaisesRegex(ValueError, 'byte limit'):
                self.compare()

    def test_decoder_bomb_rejected(self):
        with patch('PIL.Image.MAX_IMAGE_PIXELS', 2):
            with self.assertRaisesRegex(ValueError, 'decoder safety'):
                self.compare()

    def test_bad_image(self):
        self.cur.write_bytes(b'not an image')
        with self.assertRaises(OSError):
            self.compare()

    def test_metadata_redaction(self):
        meta = copy.deepcopy(self.meta)
        meta['source_uri'] = 'https://user:password@example.test/'
        result = self.compare(current_metadata=meta)
        self.assertNotIn('password', str(result))

    def test_animated_rejected(self):
        a = Image.new('RGB', (4, 4), 'red')
        b = Image.new('RGB', (4, 4), 'blue')
        a.save(self.cur, format='PNG', save_all=True, append_images=[b])
        with self.assertRaisesRegex(ValueError, 'animated'):
            self.compare()


if __name__ == '__main__':
    unittest.main()
