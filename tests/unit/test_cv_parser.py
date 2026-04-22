"""
Unit tests for the CV parsing service.

Tests text extraction from different file types and error handling.
"""

import tempfile
from pathlib import Path

import pytest

from app.core.exceptions import InternalError, UnsupportedFileTypeError
from app.services.cv_service import CVService


class TestCVServiceParseFile:
    """Tests for CVService.parse_file()."""

    def test_parse_txt_file(self, tmp_path: Path):
        """Should return the content of a TXT file."""
        cv_file = tmp_path / "cv.txt"
        cv_file.write_text("Software Engineer with 5 years of Python experience.", encoding="utf-8")
        result = CVService.parse_file(str(cv_file))
        assert "Software Engineer" in result
        assert "Python" in result

    def test_parse_txt_empty_file(self, tmp_path: Path):
        """Empty TXT file returns empty string."""
        cv_file = tmp_path / "empty.txt"
        cv_file.write_text("", encoding="utf-8")
        result = CVService.parse_file(str(cv_file))
        assert result == ""

    def test_unsupported_extension_raises_error(self, tmp_path: Path):
        """Unsupported file types raise UnsupportedFileTypeError."""
        bad_file = tmp_path / "cv.xlsx"
        bad_file.write_bytes(b"fake content")
        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            CVService.parse_file(str(bad_file))
        assert "xlsx" in str(exc_info.value.detail)

    def test_unsupported_extension_error_code(self, tmp_path: Path):
        bad_file = tmp_path / "cv.pptx"
        bad_file.write_bytes(b"fake")
        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            CVService.parse_file(str(bad_file))
        assert exc_info.value.error_code == "UNSUPPORTED_FILE_TYPE"

    def test_case_insensitive_extension(self, tmp_path: Path):
        """Extension matching is case-insensitive (.TXT, .PDF, .DOCX)."""
        cv_file = tmp_path / "cv.TXT"
        cv_file.write_text("Senior developer", encoding="utf-8")
        result = CVService.parse_file(str(cv_file))
        assert "Senior developer" in result

    def test_parse_pdf_corrupted_raises_internal_error(self, tmp_path: Path):
        """Corrupted PDF raises InternalError."""
        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(b"this is not a valid pdf")
        with pytest.raises(InternalError):
            CVService.parse_file(str(bad_pdf))

    def test_parse_docx_corrupted_raises_internal_error(self, tmp_path: Path):
        """Corrupted DOCX raises InternalError."""
        bad_docx = tmp_path / "bad.docx"
        bad_docx.write_bytes(b"this is not a valid docx")
        with pytest.raises(InternalError):
            CVService.parse_file(str(bad_docx))

    def test_txt_unicode_content(self, tmp_path: Path):
        """Should handle Unicode (French accents, etc.)."""
        cv_file = tmp_path / "cv_fr.txt"
        content = "Développeur senior avec expérience en intégration continue"
        cv_file.write_text(content, encoding="utf-8")
        result = CVService.parse_file(str(cv_file))
        assert "Développeur" in result
        assert "intégration" in result
