from __future__ import annotations

import re
from typing import Any, Iterable
from urllib.parse import urlparse

_AUTHORITY = "candidate-ranking-only"
_LINEAGE_KEYS = {"classification", "parent_chat_id", "continuation"}


def _norm_text(value: Any) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def _norm_repo(value: Any) -> str:
    raw = str(value or "").strip().rstrip("/")
    if not raw:
        return ""
    parsed = urlparse(raw)
    if parsed.scheme and parsed.netloc:
        host = parsed.netloc.casefold()
        path = parsed.path.rstrip("/")
        if path.casefold().endswith(".git"):
            path = path[:-4]
        return f"{host}{path}".casefold()
    if raw.casefold().endswith(".git"):
        raw = raw[:-4]
    return raw.casefold().rstrip("/")


def _norm_path(value: Any) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    while "//" in raw:
        raw = raw.replace("//", "/")
    return raw.rstrip("/").casefold()


def _norm_artifact(value: Any) -> str:
    return str(value or "").strip().replace("\\", "/").rsplit("/", 1)[-1].casefold()


def _values(item: dict, *keys: str) -> list[Any]:
    result: list[Any] = []
    for key in keys:
        value = item.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            result.extend(value)
        else:
            result.append(value)
    return result


def _set(item: dict, normalizer, *keys: str) -> set[str]:
    return {normalizer(x) for x in _values(item, *keys) if normalizer(x)}


def _tokens(item: dict) -> set[str]:
    text = " ".join(str(x or "") for x in _values(item, "title", "text", "content", "summary"))
    return {token.casefold() for token in re.findall(r"[\w-]{3,}", text, flags=re.UNICODE)}


def _topic_similarity(current: dict, candidate: dict) -> int:
    left = _tokens(current)
    right = _tokens(candidate)
    if not left or not right:
        return 0
    overlap = len(left & right)
    if not overlap:
        return 0
    union = len(left | right)
    return min(999, max(1, int((overlap / union) * 900) + overlap))


def _candidate_key(item: dict) -> str:
    return _norm_text(item.get("session_id") or item.get("chat_id") or item.get("title") or "")


def rank_history_candidates(current: dict, candidates: Iterable[dict]) -> list[dict]:
    """Rank candidate history without deciding lineage.

    Priority: explicit chat reference > exact repository > project+stable
    identity > exact path > project id only > unique artifact > topic.
    Scores are discovery metadata only and never prove continuation.
    """
    refs = {_norm_text(x) for x in _values(current, "continuation_refs") if _norm_text(x)}
    current_project = _norm_text(current.get("project_id"))
    current_repos = _set(current, _norm_repo, "repositories", "repository", "repo_url")
    current_paths = _set(current, _norm_path, "paths", "path", "cwd")
    current_artifacts = _set(current, _norm_artifact, "files", "artifacts", "unique_artifacts")

    ranked: list[tuple[int, str, dict]] = []
    for raw in candidates:
        candidate = dict(raw)
        candidate_names = {
            _norm_text(candidate.get("session_id")),
            _norm_text(candidate.get("chat_id")),
            _norm_text(candidate.get("title")),
        }
        candidate_names.discard("")
        explicit = bool(refs & candidate_names)
        repos = _set(candidate, _norm_repo, "repositories", "repository", "repo_url")
        paths = _set(candidate, _norm_path, "paths", "path", "cwd")
        artifacts = _set(candidate, _norm_artifact, "files", "artifacts", "unique_artifacts")
        repo_overlap = current_repos & repos
        path_overlap = current_paths & paths
        artifact_overlap = current_artifacts & artifacts
        project_match = bool(current_project and current_project == _norm_text(candidate.get("project_id")))
        topic = _topic_similarity(current, candidate)

        signals: list[str] = []
        if explicit:
            signals.append("explicit_chat_reference")
        if repo_overlap:
            signals.append("exact_repository")
        if project_match:
            signals.append("same_project_id")
        if path_overlap:
            signals.append("exact_path")
        if artifact_overlap:
            signals.append("unique_artifact")
        if topic:
            signals.append("topic_similarity")

        if explicit:
            band, reason = 6, "explicit_chat_reference"
        elif repo_overlap:
            band, reason = 5, "exact_repository"
        elif project_match and path_overlap:
            band, reason = 4, "project_plus_stable_identity"
        elif path_overlap:
            band, reason = 3, "exact_path"
        elif project_match:
            band, reason = 2, "project_id_only"
        elif artifact_overlap:
            band, reason = 1, "unique_artifact"
        elif topic:
            band, reason = 0, "topic_similarity"
        else:
            band, reason = 0, "no_stable_signal"

        if reason == "no_stable_signal":
            score = 0
        elif reason == "topic_similarity":
            score = topic
        else:
            score = band * 1000 + topic

        safe = {k: v for k, v in candidate.items() if k not in _LINEAGE_KEYS}
        safe.update({
            "authority": _AUTHORITY,
            "score": score,
            "rank_reason": reason,
            "signals": signals,
            "matched_repositories": sorted(repo_overlap),
            "matched_paths": sorted(path_overlap),
            "matched_artifacts": sorted(artifact_overlap),
            "topic_score": topic,
        })
        ranked.append((score, _candidate_key(safe), safe))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item for _, _, item in ranked]
