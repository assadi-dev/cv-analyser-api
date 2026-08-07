"""
Unit tests for ATS scoring module.

Tests keyword extraction, ATS score computation, and edge cases.
"""

import pytest

from app.agents.nodes.ats import compute_ats_score, extract_keywords, extract_vocabulary


class TestExtractKeywords:
    """Tests for the keyword extraction function."""

    def test_returns_list_of_strings(self):
        result = extract_keywords("Python developer with Django experience")
        assert isinstance(result, list)
        assert all(isinstance(k, str) for k in result)

    def test_removes_stopwords_french(self):
        result = extract_keywords("le développeur avec les compétences")
        assert "le" not in result
        assert "les" not in result
        assert "avec" not in result

    def test_removes_stopwords_english(self):
        result = extract_keywords("the developer with the skills")
        assert "the" not in result
        assert "with" not in result

    def test_removes_short_tokens(self):
        result = extract_keywords("xy zw developer")
        # Tokens under 3 chars are noise unless they are known tech terms.
        assert "xy" not in result
        assert "zw" not in result

    def test_keeps_short_tech_tokens(self):
        result = extract_keywords("AI ML JS CI developer")
        # These are real skills despite being 2 chars — see SHORT_TECH_TOKENS.
        assert {"ai", "ml", "js", "ci"} <= set(result)

    def test_folds_accents(self):
        result = extract_keywords("Développement de données et fonctionnalités")
        # Accents must not truncate the word ("développement" -> "veloppement").
        assert "developpement" in result
        assert "donnees" in result
        assert "fonctionnalites" in result
        assert "veloppement" not in result

    def test_accented_cv_matches_unaccented_job(self):
        vocabulary = extract_vocabulary("Expérience en développement de données")
        score, found, missing = compute_ats_score(vocabulary, ["developpement", "donnees"])
        assert score == 100
        assert missing == []

    def test_top_n_limit(self):
        text = " ".join([f"keyword{i}" for i in range(100)])
        result = extract_keywords(text, top_n=10)
        assert len(result) <= 10

    def test_empty_text(self):
        result = extract_keywords("")
        assert result == []

    def test_case_insensitive(self):
        result = extract_keywords("Python PYTHON python")
        # All same word — should appear once in results
        assert result.count("python") == 1

    def test_tech_keywords_preserved(self):
        result = extract_keywords("Docker Kubernetes React Node.js PostgreSQL")
        keywords_lower = [k.lower() for k in result]
        assert "docker" in keywords_lower
        assert "kubernetes" in keywords_lower
        assert "react" in keywords_lower


class TestComputeATSScore:
    """Tests for the ATS score computation function."""

    def test_perfect_match(self):
        keywords = ["python", "django", "postgresql"]
        score, found, missing = compute_ats_score(keywords, keywords)
        assert score == 100
        assert set(found) == set(keywords)
        assert missing == []

    def test_no_match(self):
        cv_keywords = ["java", "spring", "mysql"]
        job_keywords = ["python", "django", "postgresql"]
        score, found, missing = compute_ats_score(cv_keywords, job_keywords)
        assert score == 0
        assert found == []
        assert set(missing) == set(job_keywords)

    def test_partial_match(self):
        cv_keywords = ["python", "django", "java"]
        job_keywords = ["python", "django", "postgresql"]
        score, found, missing = compute_ats_score(cv_keywords, job_keywords)
        assert score == pytest.approx(67, abs=1)  # 2/3 = 66.7%
        assert "python" in found
        assert "django" in found
        assert "postgresql" in missing

    def test_empty_job_keywords(self):
        score, found, missing = compute_ats_score(["python"], [])
        assert score == 0
        assert found == []
        assert missing == []

    def test_empty_cv_keywords(self):
        job_keywords = ["python", "django"]
        score, found, missing = compute_ats_score([], job_keywords)
        assert score == 0
        assert found == []
        assert set(missing) == set(job_keywords)

    def test_score_capped_at_100(self):
        job_keywords = ["python"]
        cv_keywords = ["python", "django", "flask", "fastapi"]
        score, _, _ = compute_ats_score(cv_keywords, job_keywords)
        assert score <= 100

    def test_score_is_integer(self):
        score, _, _ = compute_ats_score(["python", "java"], ["python", "django"])
        assert isinstance(score, int)
