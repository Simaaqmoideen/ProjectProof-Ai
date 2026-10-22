"""Code similarity detection — FR-EVL-2 (deterministic; no LLM).

Uses the winnowing algorithm (k-grams + rolling minimum hash).
See docs/06-ai-modules-specification.md section 5.2.

Privacy: reports show other students' work only to admins, never to companies or students.
"""

from __future__ import annotations

import hashlib
import re
from typing import NamedTuple

# ── Configuration ─────────────────────────────────────────────────────────────

KGRAM_SIZE = 5
WINDOW_SIZE = 4

_SKIP_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".lock",
    ".min.js",
    ".map",
}
_SKIP_DIRS = {"node_modules", ".git", "__pycache__", "dist", "build", ".venv", "venv"}

_SIMILARITY_THRESHOLDS = {
    "low": 0.30,
    "high": 0.60,
}


class FileSimilarity(NamedTuple):
    file_a: str
    file_b: str
    score: float


class SimilarityResult(NamedTuple):
    score: float  # 0.0–1.0
    label: str  # "low" | "medium" | "high"
    matched_pairs: list[FileSimilarity]


# ── Normalisation ─────────────────────────────────────────────────────────────


def _normalise(source: str) -> str:
    """Strip comments, collapse whitespace, replace identifiers and literals.

    This makes renaming variables or reformatting invisible to the algorithm.
    """
    # Remove single-line comments (// and #)
    source = re.sub(r"(//[^\n]*|#[^\n]*)", "", source)
    # Remove multi-line comments (/* ... */)
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    # Replace string literals
    source = re.sub(r'"[^"]*"', '"STR"', source)
    source = re.sub(r"'[^']*'", "'STR'", source)
    # Replace numeric literals
    source = re.sub(r"\b\d+\.?\d*\b", "NUM", source)
    # Replace identifiers (words) with a placeholder — keeps keywords distinct
    source = re.sub(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", "ID", source)
    # Collapse whitespace
    source = re.sub(r"\s+", " ", source).strip()
    return source


# ── Fingerprinting ────────────────────────────────────────────────────────────


def _hash_kgram(kgram: str) -> int:
    return int(hashlib.md5(kgram.encode()).hexdigest(), 16)


def _fingerprint(text: str) -> set[int]:
    """Winnowing: build k-grams, then keep minimum hash in each window."""
    tokens = text.split()
    if len(tokens) < KGRAM_SIZE:
        # Too short — use a single hash of the whole text
        return {_hash_kgram(text)}

    kgrams = [" ".join(tokens[i : i + KGRAM_SIZE]) for i in range(len(tokens) - KGRAM_SIZE + 1)]
    hashes = [_hash_kgram(kg) for kg in kgrams]

    fingerprints: set[int] = set()
    for i in range(len(hashes) - WINDOW_SIZE + 1):
        window = hashes[i : i + WINDOW_SIZE]
        fingerprints.add(min(window))

    return fingerprints


# ── Per-file similarity ───────────────────────────────────────────────────────


def _file_similarity(fp_a: set[int], fp_b: set[int]) -> float:
    """Containment score: shared / min(|A|, |B|)."""
    if not fp_a or not fp_b:
        return 0.0
    shared = len(fp_a & fp_b)
    return shared / min(len(fp_a), len(fp_b))


# ── Public API ────────────────────────────────────────────────────────────────


def should_skip(path: str) -> bool:
    """Return True for files / directories that must be excluded."""
    parts = path.replace("\\", "/").split("/")
    for part in parts:
        if part in _SKIP_DIRS:
            return True
    _, _, ext = path.rpartition(".")
    return f".{ext.lower()}" in _SKIP_EXTENSIONS


def fingerprint_files(files: dict[str, str]) -> dict[str, set[int]]:
    """fingerprint_files({'path': 'source'}) -> {'path': fingerprint_set}."""
    result = {}
    for path, source in files.items():
        if should_skip(path):
            continue
        normalised = _normalise(source)
        result[path] = _fingerprint(normalised)
    return result


def compare_submissions(
    files_a: dict[str, str],
    files_b: dict[str, str],
    starter_template: dict[str, str] | None = None,
) -> SimilarityResult:
    """Compare two submissions and return a SimilarityResult.

    files_a / files_b: {relative_path: source_code}
    starter_template: optional starter code to exclude from comparison.

    Score = max containment across matching file pairs.
    """
    # Remove starter-template files
    if starter_template:
        template_fps = fingerprint_files(starter_template)
        for path in list(files_a.keys()):
            if path in template_fps:
                del files_a[path]
        for path in list(files_b.keys()):
            if path in template_fps:
                del files_b[path]

    fp_a = fingerprint_files(files_a)
    fp_b = fingerprint_files(files_b)

    if not fp_a or not fp_b:
        return SimilarityResult(score=0.0, label="low", matched_pairs=[])

    # Compare every file pair (a_path, b_path)
    matched_pairs: list[FileSimilarity] = []
    max_score = 0.0

    for path_a, fps_a in fp_a.items():
        for path_b, fps_b in fp_b.items():
            s = _file_similarity(fps_a, fps_b)
            if s >= _SIMILARITY_THRESHOLDS["low"]:
                matched_pairs.append(FileSimilarity(path_a, path_b, round(s, 4)))
            max_score = max(max_score, s)

    # Sort by score descending
    matched_pairs.sort(key=lambda x: x.score, reverse=True)

    # Assign label
    if max_score >= _SIMILARITY_THRESHOLDS["high"]:
        label = "high"
    elif max_score >= _SIMILARITY_THRESHOLDS["low"]:
        label = "medium"
    else:
        label = "low"

    return SimilarityResult(
        score=round(max_score, 4),
        label=label,
        matched_pairs=matched_pairs[:20],  # cap the report
    )
