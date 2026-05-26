"""Tests for RetrievalQualityService — scoring, filtering, dedup, match quality."""

import pytest

from app.services.retrieval_quality_service import (
    MatchQuality,
    QualityEvaluation,
    RetrievalCandidate,
    RetrievalQualityPolicy,
    RetrievalQualityService,
    RetrievalStrictness,
    _compute_keyword_score,
    _compute_rule_score,
    _extract_anchors,
    normalize_score,
    ScoreProfile,
    PROVIDER_SCORE_PROFILES,
)


# --- Fixtures ---


def _make_candidate(
    chunk_id: str = "c1",
    source_id: str = "s1",
    heading: str = "魔法体系概述",
    content: str = "魔法体系包括元素魔法和咒语魔法，是战斗的基础。魔法师需要长期修炼才能掌握。",
    index: int = 0,
    title: str = "魔法体系设定",
    source_type: str = "note",
    credibility: str = "high",
    tags: list[str] | None = None,
    vector_score: float | None = None,
    keyword_score: float | None = None,
) -> RetrievalCandidate:
    return RetrievalCandidate(
        chunk_id=chunk_id,
        source_id=source_id,
        chunk_heading=heading,
        chunk_content=content,
        chunk_index=index,
        source_title=title,
        source_type=source_type,
        source_credibility=credibility,
        source_tags=tags or [],
        vector_score=vector_score,
        keyword_score=keyword_score,
    )


@pytest.fixture
def service() -> RetrievalQualityService:
    return RetrievalQualityService()


# --- Anchor Extraction ---


class TestExtractAnchors:
    def test_chinese_phrase_extraction(self):
        # CJK regex matches consecutive CJK chars as one phrase
        anchors = _extract_anchors("魔法体系如何构成")
        # The whole CJK sequence is extracted as one anchor (not split)
        assert "魔法体系如何构成" in anchors

    def test_english_token_extraction(self):
        anchors = _extract_anchors("Python 编程基础")
        assert "python" in anchors  # lowercased
        assert "编程基础" in anchors

    def test_stop_words_filtered(self):
        # "什么是魔法体系" → CJK regex extracts the full phrase
        # since stop words are checked against exact matches
        anchors = _extract_anchors("什么是魔法体系")
        assert "什么是魔法体系" in anchors

    def test_separate_phrases_extracted(self):
        # When separated by spaces, each CJK group is its own anchor
        anchors = _extract_anchors("魔法体系 构成要素")
        assert "魔法体系" in anchors
        assert "构成要素" in anchors

    def test_empty_query_returns_empty(self):
        assert _extract_anchors("") == []
        assert _extract_anchors("   ") == []

    def test_short_query_fallback(self):
        anchors = _extract_anchors("火")
        # Short query with ≤4 chars falls back to keeping the whole query
        assert "火" in anchors

    def test_mixed_chinese_english(self):
        anchors = _extract_anchors("RAG 检索增强生成")
        assert "rag" in anchors
        assert "检索增强生成" in anchors


# --- Score Normalization ---


class TestNormalizeScore:
    def test_bigram_hash_profile(self):
        profile = PROVIDER_SCORE_PROFILES["bigram-hash-v1"]
        # 0.0 → 0.0, 0.25 → 0.5, 0.5 → 1.0
        assert normalize_score(0.0, profile) == pytest.approx(0.0)
        assert normalize_score(0.25, profile) == pytest.approx(0.5)
        assert normalize_score(0.5, profile) == pytest.approx(1.0)

    def test_dashscope_profile(self):
        profile = PROVIDER_SCORE_PROFILES["dashscope-text-v1"]
        # floor=0.2, ceiling=0.95
        assert normalize_score(0.2, profile) == pytest.approx(0.0)
        assert normalize_score(0.575, profile) == pytest.approx(0.5)
        assert normalize_score(0.95, profile) == pytest.approx(1.0)

    def test_clamping_below_floor(self):
        profile = ScoreProfile(floor=0.2, ceiling=0.8)
        assert normalize_score(0.0, profile) == 0.0

    def test_clamping_above_ceiling(self):
        profile = ScoreProfile(floor=0.0, ceiling=0.5)
        assert normalize_score(0.8, profile) == 1.0

    def test_zero_span_returns_zero(self):
        profile = ScoreProfile(floor=0.5, ceiling=0.5)
        assert normalize_score(0.5, profile) == 0.0


# --- Keyword Scoring ---


class TestComputeKeywordScore:
    def test_title_match_weights_higher(self):
        candidate = _make_candidate(title="魔法体系")
        anchors = ["魔法体系"]
        score = _compute_keyword_score(candidate, anchors)
        assert score > 0.9  # title match should yield high score

    def test_content_only_match(self):
        candidate = _make_candidate(
            title="无关标题",
            heading="",
            content="魔法体系包括元素魔法和咒语魔法，是战斗的基础。魔法师需要长期修炼才能掌握。",
        )
        anchors = ["魔法体系"]
        score = _compute_keyword_score(candidate, anchors)
        assert 0.0 < score < 0.5  # content-only match is lower

    def test_no_anchor_match_returns_zero(self):
        candidate = _make_candidate(title="无关", content="一些无关的内容在这里展示。")
        anchors = ["完全不匹配"]
        score = _compute_keyword_score(candidate, anchors)
        assert score == 0.0

    def test_empty_anchors_returns_zero(self):
        candidate = _make_candidate()
        assert _compute_keyword_score(candidate, []) == 0.0

    def test_tag_match_contributes(self):
        candidate = _make_candidate(
            title="无关标题",
            content="无关的内容展示在这里面",
            tags=["魔法体系", "战斗"],
        )
        anchors = ["魔法体系"]
        score = _compute_keyword_score(candidate, anchors)
        assert score > 0.0

    def test_multiple_anchors_accumulate(self):
        candidate = _make_candidate(
            title="魔法体系概述",
            heading="元素魔法详解",
            content="魔法体系包括元素魔法和咒语魔法，是战斗的基础。魔法师需要长期修炼才能掌握。",
        )
        anchors = ["魔法体系", "元素魔法"]
        score = _compute_keyword_score(candidate, anchors)
        assert score > 0.5


# --- Rule Scoring ---


class TestComputeRuleScore:
    def test_high_credibility_long_content(self):
        candidate = _make_candidate(
            credibility="high",
            content="魔法体系包括元素魔法和咒语魔法两大类，是战斗的基础能力。"
                    "魔法师需要经过长期修炼才能逐步掌握各种复杂的魔法技能。",
        )
        score = _compute_rule_score(candidate)
        assert score == pytest.approx(1.0)

    def test_low_credibility(self):
        candidate = _make_candidate(
            credibility="low",
            content="魔法体系包括元素魔法和咒语魔法两大类，是战斗的基础能力。"
                    "魔法师需要经过长期修炼才能逐步掌握各种复杂的魔法技能。",
        )
        score = _compute_rule_score(candidate)
        assert score == pytest.approx(0.2)

    def test_medium_credibility(self):
        candidate = _make_candidate(
            credibility="medium",
            content="魔法体系包括元素魔法和咒语魔法两大类，是战斗的基础能力。"
                    "魔法师需要经过长期修炼才能逐步掌握各种复杂的魔法技能。",
        )
        score = _compute_rule_score(candidate)
        assert score == pytest.approx(0.5)

    def test_unknown_credibility_default(self):
        candidate = _make_candidate(
            credibility="unknown",
            content="魔法体系包括元素魔法和咒语魔法两大类，是战斗的基础能力。"
                    "魔法师需要经过长期修炼才能逐步掌握各种复杂的魔法技能。",
        )
        score = _compute_rule_score(candidate)
        assert score == pytest.approx(0.3)

    def test_short_content_penalty(self):
        candidate = _make_candidate(content="短内容测试")
        score = _compute_rule_score(candidate)
        # Length < 20 chars → 0.2 factor, credibility "high" → 1.0
        assert score == pytest.approx(0.2)

    def test_medium_content_factor(self):
        candidate = _make_candidate(
            content="这是一段中等长度的内容，用于测试内容长度因子的计算是否正确。",
            credibility="high",
        )
        score = _compute_rule_score(candidate)
        # Length >= 20 but < 50 → 0.5, high → 1.0
        assert score == pytest.approx(0.5)


# --- Evaluate Candidates ---


class TestEvaluateCandidates:
    def test_basic_evaluation_returns_results(self, service: RetrievalQualityService):
        candidates = [_make_candidate(vector_score=0.4, keyword_score=0.8)]
        result = service.evaluate_candidates(
            query="魔法体系",
            candidates=candidates,
            strictness="broad",
            mode="hybrid",
            provider_model_name="bigram-hash-v1",
            limit=10,
        )
        assert isinstance(result, QualityEvaluation)
        assert result.candidate_count == 1
        assert len(result.results) >= 1

    def test_dedup_by_chunk_id(self, service: RetrievalQualityService):
        c1 = _make_candidate(chunk_id="c1", vector_score=0.4)
        c2 = _make_candidate(chunk_id="c1", vector_score=0.3)  # duplicate
        c3 = _make_candidate(chunk_id="c2", vector_score=0.4)
        result = service.evaluate_candidates(
            query="魔法",
            candidates=[c1, c2, c3],
            strictness="broad",
            mode="semantic",
            provider_model_name=None,
            limit=10,
        )
        # Should deduplicate c1, keeping first occurrence
        chunk_ids = [r.candidate.chunk_id for r in result.results]
        assert chunk_ids.count("c1") <= 1

    def test_short_content_filtered(self, service: RetrievalQualityService):
        candidate = _make_candidate(
            content="太短",
            vector_score=0.5,
        )
        result = service.evaluate_candidates(
            query="魔法",
            candidates=[candidate],
            strictness="broad",
            mode="semantic",
            provider_model_name=None,
            limit=10,
        )
        assert len(result.results) == 0
        assert result.filtered_count > 0

    def test_strict_filters_more_than_broad(self, service: RetrievalQualityService):
        # Create a candidate with mediocre scores
        candidate = _make_candidate(
            title="不相关",
            heading="",
            content="这是一段与查询完全无关的内容，用于测试过滤效果。",
            credibility="low",
            vector_score=0.1,
        )
        strict = service.evaluate_candidates(
            query="魔法体系",
            candidates=[candidate],
            strictness="strict",
            mode="semantic",
            provider_model_name=None,
            limit=10,
        )
        broad = service.evaluate_candidates(
            query="魔法体系",
            candidates=[candidate],
            strictness="broad",
            mode="semantic",
            provider_model_name=None,
            limit=10,
        )
        assert len(strict.results) <= len(broad.results)

    def test_limit_applied(self, service: RetrievalQualityService):
        candidates = [
            _make_candidate(
                chunk_id=f"c{i}",
                vector_score=0.4,
                keyword_score=0.8,
            )
            for i in range(20)
        ]
        result = service.evaluate_candidates(
            query="魔法体系",
            candidates=candidates,
            strictness="broad",
            mode="hybrid",
            provider_model_name="bigram-hash-v1",
            limit=5,
        )
        assert len(result.results) <= 5

    def test_sorted_by_final_score_desc(self, service: RetrievalQualityService):
        candidates = [
            _make_candidate(chunk_id="c1", vector_score=0.1, keyword_score=0.3),
            _make_candidate(chunk_id="c2", vector_score=0.4, keyword_score=0.9),
            _make_candidate(chunk_id="c3", vector_score=0.25, keyword_score=0.6),
        ]
        result = service.evaluate_candidates(
            query="魔法体系",
            candidates=candidates,
            strictness="broad",
            mode="hybrid",
            provider_model_name="bigram-hash-v1",
            limit=10,
        )
        if len(result.results) >= 2:
            scores = [r.final_score for r in result.results]
            assert scores == sorted(scores, reverse=True)

    def test_match_quality_assigned(self, service: RetrievalQualityService):
        # High-scoring candidate
        candidate = _make_candidate(
            title="魔法体系",
            heading="魔法体系概述",
            content="魔法体系包括元素魔法和咒语魔法，是战斗的基础。魔法师需要长期修炼才能掌握。",
            credibility="high",
            vector_score=0.45,
            keyword_score=1.0,
        )
        result = service.evaluate_candidates(
            query="魔法体系",
            candidates=[candidate],
            strictness="broad",
            mode="hybrid",
            provider_model_name="bigram-hash-v1",
            limit=10,
        )
        if result.results:
            assert result.results[0].match_quality in ("high", "medium", "low")
            assert isinstance(result.results[0].match_reason, str)
            assert len(result.results[0].match_reason) > 0

    def test_hard_floor_rejection(self, service: RetrievalQualityService):
        # Very low vector score and no keyword match
        candidate = _make_candidate(
            title="无关标题",
            heading="",
            content="这是一段完全无关的内容描述信息",
            credibility="low",
            vector_score=0.001,
        )
        result = service.evaluate_candidates(
            query="魔法体系构成",
            candidates=[candidate],
            strictness="broad",
            mode="semantic",
            provider_model_name=None,
            limit=10,
        )
        # Should be rejected by hard floor (vec_norm < 0.05 and kw < 0.1)
        assert len(result.results) == 0

    def test_all_filtered_generates_warning(self, service: RetrievalQualityService):
        candidates = [
            _make_candidate(
                chunk_id=f"c{i}",
                title="无关",
                content="短",
                vector_score=0.001,
            )
            for i in range(5)
        ]
        result = service.evaluate_candidates(
            query="魔法",
            candidates=candidates,
            strictness="strict",
            mode="semantic",
            provider_model_name=None,
            limit=10,
        )
        assert len(result.results) == 0
        assert len(result.warnings) > 0

    def test_empty_candidates(self, service: RetrievalQualityService):
        result = service.evaluate_candidates(
            query="魔法",
            candidates=[],
            strictness="balanced",
            mode="keyword",
            provider_model_name=None,
            limit=10,
        )
        assert result.candidate_count == 0
        assert result.filtered_count == 0
        assert len(result.results) == 0


# --- Policy ---


class TestRetrievalQualityPolicy:
    def test_default_thresholds(self):
        policy = RetrievalQualityPolicy()
        assert policy.min_score_for("strict") == pytest.approx(0.55)
        assert policy.min_score_for("balanced") == pytest.approx(0.35)
        assert policy.min_score_for("broad") == pytest.approx(0.15)

    def test_weights_for_mode(self):
        policy = RetrievalQualityPolicy()
        assert policy.weights_for("semantic")[0] > policy.weights_for("semantic")[1]
        assert policy.weights_for("keyword")[0] == 0.0  # no vector weight
        assert policy.weights_for("hybrid")[0] > 0.0
        assert policy.weights_for("unknown") == policy.keyword_weights


# --- Custom Policy ---


class TestCustomPolicy:
    def test_custom_thresholds(self):
        policy = RetrievalQualityPolicy(
            min_score_strict=0.9,
            min_score_balanced=0.5,
            min_score_broad=0.1,
        )
        service = RetrievalQualityService(policy=policy)
        assert service._policy.min_score_for("strict") == pytest.approx(0.9)
