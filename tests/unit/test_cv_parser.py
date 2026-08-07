"""
Unit tests for the CV text extraction service.

Tests text extraction from different file types and error handling.
"""

from pathlib import Path

import pytest

from app.core.exceptions import InternalError, UnsupportedFileTypeError
from app.services.extract_text_service import ExtractTextService


@pytest.fixture
def service() -> ExtractTextService:
    return ExtractTextService()


class TestExtractText:
    """Tests for ExtractTextService.extract_text() — the extension dispatcher."""

    def test_parse_txt_file(self, service: ExtractTextService, tmp_path: Path):
        """Should return the content of a TXT file."""
        cv_file = tmp_path / "cv.txt"
        cv_file.write_text("Software Engineer with 5 years of Python experience.", encoding="utf-8")
        result = service.extract_text(cv_file)
        assert "Software Engineer" in result
        assert "Python" in result

    def test_parse_txt_empty_file(self, service: ExtractTextService, tmp_path: Path):
        """Empty TXT file returns empty string."""
        cv_file = tmp_path / "empty.txt"
        cv_file.write_text("", encoding="utf-8")
        result = service.extract_text(cv_file)
        assert result == ""

    def test_unsupported_extension_raises_error(self, service: ExtractTextService, tmp_path: Path):
        """Unsupported file types raise UnsupportedFileTypeError."""
        bad_file = tmp_path / "cv.xlsx"
        bad_file.write_bytes(b"fake content")
        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            service.extract_text(bad_file)
        assert "xlsx" in str(exc_info.value.detail)

    def test_unsupported_extension_error_code(self, service: ExtractTextService, tmp_path: Path):
        bad_file = tmp_path / "cv.pptx"
        bad_file.write_bytes(b"fake")
        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            service.extract_text(bad_file)
        assert exc_info.value.error_code == "UNSUPPORTED_FILE_TYPE"
        assert exc_info.value.status_code == 415

    def test_case_insensitive_extension(self, service: ExtractTextService, tmp_path: Path):
        """Extension matching is case-insensitive (.TXT, .PDF, .DOCX)."""
        cv_file = tmp_path / "cv.TXT"
        cv_file.write_text("Senior developer", encoding="utf-8")
        result = service.extract_text(cv_file)
        assert "Senior developer" in result

    def test_parse_pdf_corrupted_raises_internal_error(
        self, service: ExtractTextService, tmp_path: Path
    ):
        """Corrupted PDF raises InternalError."""
        bad_pdf = tmp_path / "bad.pdf"
        bad_pdf.write_bytes(b"this is not a valid pdf")
        with pytest.raises(InternalError):
            service.extract_text(bad_pdf)

    def test_parse_docx_corrupted_raises_internal_error(
        self, service: ExtractTextService, tmp_path: Path
    ):
        """Corrupted DOCX raises InternalError."""
        bad_docx = tmp_path / "bad.docx"
        bad_docx.write_bytes(b"this is not a valid docx")
        with pytest.raises(InternalError):
            service.extract_text(bad_docx)

    def test_txt_unicode_content(self, service: ExtractTextService, tmp_path: Path):
        """Should handle Unicode (French accents, etc.)."""
        cv_file = tmp_path / "cv_fr.txt"
        content = "Développeur senior avec expérience en intégration continue"
        cv_file.write_text(content, encoding="utf-8")
        result = service.extract_text(cv_file)
        assert "Développeur" in result
        assert "intégration" in result

    def test_no_extension_raises_unsupported(self, service: ExtractTextService, tmp_path: Path):
        """A file without an extension is rejected, not silently parsed as PDF."""
        cv_file = tmp_path / "cv"
        cv_file.write_text("Some content", encoding="utf-8")
        with pytest.raises(UnsupportedFileTypeError):
            service.extract_text(cv_file)


class TestExtractTextRouting:
    """Each extension must reach its own parser, not the PDF one."""

    def test_docx_is_not_routed_to_pdf_parser(
        self, service: ExtractTextService, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        called: list[str] = []

        def record(name: str):
            return lambda self, path: called.append(name) or ""

        monkeypatch.setattr(ExtractTextService, "extract_text_from_pdf", record("pdf"))
        monkeypatch.setattr(ExtractTextService, "extract_text_from_docx", record("docx"))

        docx_file = tmp_path / "cv.docx"
        docx_file.write_bytes(b"irrelevant - the parser is stubbed")
        service.extract_text(docx_file)

        assert called == ["docx"]
