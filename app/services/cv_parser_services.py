"""
CV parsing service — extracts plain text from PDF, DOCX, and TXT files.
"""

from pathlib import Path

from app.core.exceptions import UnsupportedFileTypeError
from app.core.logging import get_logger
from app.services.extract_text_service import ExtractTextService
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
        extract_text_service = ExtractTextService()

        match suffix:
            case ".pdf":
                return extract_text_service.extract_text_from_pdf(path)
            case ".docx":
                return extract_text_service.extract_text_from_docx(path)
            case ".txt":
                return extract_text_service.extract_text_from_txt(path)
            case _:
                raise UnsupportedFileTypeError(
                    detail=f"Cannot parse file with extension '{suffix}'"
                )

