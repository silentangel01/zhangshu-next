"""Retrieval quality layer — scoring, filtering, and re-ranking.

Sits between raw candidate retrieval (vector store / keyword search) and
the final response construction in RetrievalService.  Responsible for:

1. Extracting query anchors (Chinese phrases, English/digit tokens).
2. Scoring candidates: vector_score, keyword_score, rule_score.
3. Computing a weighted final_score.
4. Filtering by strictness threshold.
5. Re-ranking and returning match_quality + match_reason.

No database access — candidates are provided by the caller.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

# --- Type aliases ---

RetrievalStrictness = Literal["strict", "balanced", "broad"]
MatchQuality = Literal["high", "medium", "low"]

# --- Stop words for anchor extraction ---

_STOP_WORDS: frozenset[str] = frozenset({
    "什么", "如何", "介绍", "设定", "资料", "内容", "哪些", "告诉",
    "描述", "关于", "有没有", "是什么", "怎么样", "可以", "帮我",
    "请问", "哪些", "哪里", "多少", "为什么", "怎么", "这个",
    "那个", "一个", "一些", "所有", "全部", "看看", "查找",
    "搜索", "一下", "知道", "能够", "是否", "哪些人",
})

# Chinese phrase extraction: sequences of 2+ CJK characters
_CJK_RE = re.compile(r"[一-鿿]{2,}")
# English/digit tokens: 2+ alphanumeric chars
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]{2,}")

# --- Score profiles per provider ---


@dataclass(frozen=True)
class ScoreProfile:
    """Expected cosine similarity range for a given embedding provider."""

    floor: float
    ceiling: float


PROVIDER_SCORE_PROFILES: dict[str, ScoreProfile] = {
    "bigram-hash-v1": ScoreProfile(floor=0.0, ceiling=0.5),
    "dashscope-text-v1": ScoreProfile(floor=0.2, ceiling=0.95),
}
DEFAULT_SCORE_PROFILE = ScoreProfile(floor=0.0, ceiling=1.0)


def normalize_score(raw: float, profile: ScoreProfile) -> float:
    """Linear-rescale *raw* from [floor, ceiling] to [0, 1], clamped."""
    span = profile.ceiling - profile.floor
    if span <= 0:
        return 0.0
    return max(0.0, min(1.0, (raw - profile.floor) / span))


# --- Policy ---


@dataclass(frozen=True)
class RetrievalQualityPolicy:
    """Centralised thresholds and weights for the quality layer."""

    # Strictness thresholds on normalised final_score
    min_score_strict: float = 0.55
    min_score_balanced: float = 0.35
    min_score_broad: float = 0.15

    # Scoring weights: (vector, keyword, rule)
    semantic_weights: tuple[float, float, float] = (0.78, 0.17, 0.05)
    hybrid_weights: tuple[float, float, float] = (0.55, 0.35, 0.10)
    keyword_weights: tuple[float, float, float] = (0.0, 0.75, 0.25)

    # Match quality boundaries on final_score
    high_threshold: float = 0.55
    medium_threshold: float = 0.35

    # Hard floor: below this normalised vector_score AND no keyword
    # anchor hit → reject regardless of strictness
    hard_floor: float = 0.05

    # Minimum content length in chars for a valid candidate
    min_content_length: int = 10

    def min_score_for(self, strictness: RetrievalStrictness) -> float:
        return {
            "strict": self.min_score_strict,
            "balanced": self.min_score_balanced,
            "broad": self.min_score_broad,
        }[strictness]

    def weights_for(self, mode: str) -> tuple[float, float, float]:
        if mode == "semantic":
            return self.semantic_weights
        if mode == "hybrid":
            return self.hybrid_weights
        return self.keyword_weights


# --- Candidate / Result dataclasses ---


@dataclass
class RetrievalCandidate:
    """Input to the quality layer — built by RetrievalService, not here."""

    chunk_id: str
    source_id: str
    chunk_heading: str
    chunk_content: str
    chunk_index: int
    source_title: str
    source_type: str
    source_credibility: str
    source_tags: list[str] = field(default_factory=list)
    vector_score: float | None = None
    keyword_score: float | None = None


@dataclass
class RetrievalQualityResult:
    """Scored and ranked result from the quality layer."""

    candidate: RetrievalCandidate
    vector_score_norm: float
    keyword_score_norm: float
    rule_score: float
    final_score: float
    match_quality: MatchQuality
    match_reason: str


@dataclass
class QualityEvaluation:
    """Full output of evaluate_candidates()."""

    results: list[RetrievalQualityResult]
    candidate_count: int
    filtered_count: int
    warnings: list[str] = field(default_factory=list)


# --- Credibility mapping ---

_CREDIBILITY_MAP: dict[str, float] = {
    "high": 1.0,
    "medium": 0.5,
    "low": 0.2,
}
_CREDIBILITY_DEFAULT = 0.3

# --- Keyword scoring field weights ---

_FIELD_WEIGHTS = {
    "source_title": 3.0,
    "chunk_heading": 2.0,
    "source_tags": 1.5,
    "chunk_content": 1.0,
}


# --- Service ---


class RetrievalQualityService:
    """Evaluate, filter, and re-rank retrieval candidates."""

    def __init__(self, policy: RetrievalQualityPolicy | None = None):
        self._policy = policy or RetrievalQualityPolicy()

    # -- public API --

    def evaluate_candidates(
        self,
        query: str,
        candidates: list[RetrievalCandidate],
        strictness: RetrievalStrictness,
        mode: str,
        provider_model_name: str | None,
        limit: int,
    ) -> QualityEvaluation:
        """Score, filter, and re-rank *candidates*.

        Returns a QualityEvaluation with accepted results, diagnostics,
        and warnings.
        """
        profile = _resolve_profile(provider_model_name)
        anchors = _extract_anchors(query)
        weights = self._policy.weights_for(mode)
        min_score = self._policy.min_score_for(strictness)

        candidate_count = len(candidates)
        warnings: list[str] = []

        # Deduplicate by chunk_id (keep first occurrence)
        seen: set[str] = set()
        unique: list[RetrievalCandidate] = []
        for c in candidates:
            if c.chunk_id not in seen:
                seen.add(c.chunk_id)
                unique.append(c)

        scored: list[RetrievalQualityResult] = []
        for c in unique:
            # --- content length filter ---
            content = c.chunk_content.strip()
            if len(content) < self._policy.min_content_length:
                continue

            # --- normalise vector score ---
            raw_vec = c.vector_score if c.vector_score is not None else 0.0
            vec_norm = normalize_score(raw_vec, profile)

            # --- keyword score ---
            kw_raw = c.keyword_score if c.keyword_score is not None else 0.0
            if kw_raw <= 0.0 and anchors:
                kw_norm = _compute_keyword_score(c, anchors)
            else:
                kw_norm = min(1.0, max(0.0, kw_raw))

            # --- rule score ---
            rule = _compute_rule_score(c)

            # --- final score ---
            final = (
                weights[0] * vec_norm
                + weights[1] * kw_norm
                + weights[2] * rule
            )

            # --- hard floor rejection ---
            if (
                vec_norm < self._policy.hard_floor
                and kw_norm < 0.1
            ):
                continue

            # --- threshold filter ---
            if final < min_score:
                continue

            # --- match quality ---
            quality: MatchQuality
            if final >= self._policy.high_threshold:
                quality = "high"
            elif final >= self._policy.medium_threshold:
                quality = "medium"
            else:
                quality = "low"

            # --- match reason ---
            reason = _build_match_reason(
                vec_norm, kw_norm, rule, anchors, weights
            )

            scored.append(
                RetrievalQualityResult(
                    candidate=c,
                    vector_score_norm=vec_norm,
                    keyword_score_norm=kw_norm,
                    rule_score=rule,
                    final_score=final,
                    match_quality=quality,
                    match_reason=reason,
                )
            )

        # Sort by final_score descending
        scored.sort(key=lambda r: r.final_score, reverse=True)

        # Apply limit
        accepted = scored[:limit]
        filtered_count = candidate_count - len(accepted)

        if filtered_count > 0 and len(accepted) == 0:
            warnings.append("所有候选结果相关度不足，已被过滤。")

        return QualityEvaluation(
            results=accepted,
            candidate_count=candidate_count,
            filtered_count=filtered_count,
            warnings=warnings,
        )


# --- Internal helpers ---


def _resolve_profile(model_name: str | None) -> ScoreProfile:
    if model_name and model_name in PROVIDER_SCORE_PROFILES:
        return PROVIDER_SCORE_PROFILES[model_name]
    return DEFAULT_SCORE_PROFILE


def _extract_anchors(query: str) -> list[str]:
    """Extract meaningful search anchors from a query string."""
    query = query.strip()
    if not query:
        return []

    # Normalise: collapse whitespace, lowercase English
    normalised = re.sub(r"\s+", " ", query).strip()

    anchors: list[str] = []

    # Extract Chinese phrases (≥2 chars)
    for match in _CJK_RE.finditer(normalised):
        phrase = match.group()
        if phrase not in _STOP_WORDS:
            anchors.append(phrase)

    # Extract English/digit tokens (≥2 chars)
    for match in _TOKEN_RE.finditer(normalised):
        token = match.group().lower()
        if token not in _STOP_WORDS:
            anchors.append(token)

    # Short query fallback: keep the whole query as an anchor
    if len(normalised) <= 4 and not anchors:
        anchors.append(normalised)

    return anchors


def _compute_keyword_score(
    candidate: RetrievalCandidate, anchors: list[str]
) -> float:
    """Score how well candidate fields match query anchors."""
    if not anchors:
        return 0.0

    fields = {
        "source_title": candidate.source_title.lower(),
        "chunk_heading": (candidate.chunk_heading or "").lower(),
        "source_tags": " ".join(candidate.source_tags).lower(),
        "chunk_content": candidate.chunk_content.lower(),
    }

    total_weight = 0.0
    for anchor in anchors:
        anchor_lower = anchor.lower()
        for field_name, field_text in fields.items():
            if anchor_lower in field_text:
                total_weight += _FIELD_WEIGHTS[field_name]

    max_possible = len(anchors) * _FIELD_WEIGHTS["source_title"]
    return min(1.0, total_weight / max(1.0, max_possible))


def _compute_rule_score(candidate: RetrievalCandidate) -> float:
    """Heuristic score based on credibility and content quality."""
    cred = _CREDIBILITY_MAP.get(
        candidate.source_credibility, _CREDIBILITY_DEFAULT
    )

    content_len = len(candidate.chunk_content.strip())
    if content_len < 20:
        length_factor = 0.2
    elif content_len < 50:
        length_factor = 0.5
    else:
        length_factor = 1.0

    return cred * length_factor


def _build_match_reason(
    vec_norm: float,
    kw_norm: float,
    rule: float,
    anchors: list[str],
    weights: tuple[float, float, float],
) -> str:
    """Generate a human-readable Chinese match reason string."""
    w_vec, w_kw, _ = weights
    vec_contrib = w_vec * vec_norm
    kw_contrib = w_kw * kw_norm

    if vec_contrib > kw_contrib * 1.5:
        if vec_norm >= 0.7:
            return "语义相似度较高"
        return "语义匹配"

    if kw_contrib > vec_contrib * 1.5:
        matched = anchors[:3]
        if matched:
            return "关键词命中: " + "、".join(matched)
        return "关键词匹配"

    return "语义 + 关键词综合匹配"
