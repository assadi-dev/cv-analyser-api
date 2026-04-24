"""
CV parsing service — extracts plain text from PDF, DOCX, and TXT files.
"""

from pathlib import Path

from app.core.exceptions import InternalError, UnsupportedFileTypeError
from app.core.logging import get_logger
import PyPDF2
import docx

logger = get_logger(__name__)

class CVParserService:
    """Parses CV files into plain text for AI analysis."""

    @staticmethod
    def parse_file(file_path: str) -> str:
        """
        Extracts plain text from a CV file.

        Args:
            file_path: Absolute or relative path to the CV file.

        Returns:
            Extracted plain text string.

        Raises:
            UnsupportedFileTypeError: File extension not supported.
            InternalError:            Parsing failed unexpectedly.
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        match suffix:
            case ".pdf":
                return CVParserService._parse_pdf(path)
            case ".docx":
                return CVParserService._parse_docx(path)
            case ".txt":
                return path.read_text(encoding="utf-8")
            case _:
                raise UnsupportedFileTypeError(
                    detail=f"Cannot parse file with extension '{suffix}'"
                )

    @staticmethod
    def _parse_pdf(path: Path) -> str:
        """Extracts text from a PDF file using PyPDF2."""
        try:
          

            text_parts: list[str] = []
            with path.open("rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)

            full_text = "\n".join(text_parts).strip()
            logger.info(
                "PDF parsed",
                extra={"path": str(path), "pages": len(text_parts), "chars": len(full_text)},
            )
            return full_text

        except Exception as exc:
            logger.error("PDF parsing failed", exc_info=exc, extra={"path": str(path)})
            raise InternalError(detail=f"Failed to parse PDF: {exc}") from exc

    @staticmethod
    def _parse_docx(path: Path) -> str:
        """Extracts text from a DOCX file using python-docx."""
        try:

            doc = docx.Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            full_text = "\n".join(paragraphs).strip()

            logger.info(
                "DOCX parsed",
                extra={"path": str(path), "paragraphs": len(paragraphs), "chars": len(full_text)},
            )
            return full_text

        except Exception as exc:
            logger.error("DOCX parsing failed", exc_info=exc, extra={"path": str(path)})
            raise InternalError(detail=f"Failed to parse DOCX: {exc}") from exc