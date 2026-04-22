"""
Unit tests for the global score computation.

Tests the weighted scoring formula without any LLM calls.
"""

import pytest

from app.agents.nodes.scorer import compute_global_score


class TestComputeGlobalScore:
    """Tests for the weighted global score formula."""

    def test_perfect_scores(self):
        score = compute_global_score(
            score_ats=100,
            score_competences=100,
            score_experience=100,
        )
        assert score == 100

    def test_zero_scores(self):
        score = compute_global_score(
            score_ats=0,
            score_competences=0,
            score_experience=0,
        )
        assert score == 0

    def test_weighted_formula(self):
        """
        Verify weights: ATS=30%, competences=45%, experience=25%
        Input: ATS=100, competences=0, experience=0 → expected 30
        """
        score = compute_global_score(
            score_ats=100,
            score_competences=0,
            score_experience=0,
        )
        assert score == 30

    def test_competences_weight(self):
        """competences=100, rest=0 → expected 45"""
        score = compute_global_score(
            score_ats=0,
            score_competences=100,
            score_experience=0,
        )
        assert score == 45

    def test_experience_weight(self):
        """experience=100, rest=0 → expected 25"""
        score = compute_global_score(
            score_ats=0,
            score_competences=0,
            score_experience=100,
        )
        assert score == 25

    def test_result_is_integer(self):
        score = compute_global_score(
            score_ats=72,
            score_competences=85,
            score_experience=78,
        )
        assert isinstance(score, int)

    def test_realistic_case(self):
        """Realistic scenario: decent ATS, good competences, average experience."""
        score = compute_global_score(
            score_ats=72,
            score_competences=88,
            score_experience=75,
        )
        # Expected: 72*0.3 + 88*0.45 + 75*0.25 = 21.6 + 39.6 + 18.75 = 79.95 → 80
        assert score == 80

    def test_score_within_bounds(self):
        """Score should always be between 0 and 100."""
        for ats, comp, exp in [(0, 0, 0), (100, 100, 100), (50, 70, 60)]:
            score = compute_global_score(ats, comp, exp)
            assert 0 <= score <= 100

    @pytest.mark.parametrize("ats,comp,exp,expected", [
        (100, 100, 100, 100),
        (0, 0, 0, 0),
        (100, 0, 0, 30),
        (0, 100, 0, 45),
        (0, 0, 100, 25),
        (72, 88, 75, 80),
    ])
    def test_parametrized_cases(self, ats: int, comp: int, exp: int, expected: int):
        score = compute_global_score(ats, comp, exp)
        assert score == expected
