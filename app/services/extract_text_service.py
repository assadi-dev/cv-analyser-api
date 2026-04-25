from pathlib import Path
from app.core.exceptions import InternalError, UnsupportedFileTypeError
from app.core.logging import get_logger
import PyPDF2
import docx

logger = get_logger(__name__)



class ExtractTextService:


    def extract_text_from_pdf(self, path: Path) -> str:
        """Extracts text from a PDF file using PyPDF2."""
        try:
            extension = path.suffix.lower()
            if not extension == ".pdf":
                raise UnsupportedFileTypeError(detail="File is not a PDF")

            text_parts: list[str] = []
          
            with path.open("rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text() or ""
                    text_parts.append(page_text)

            full_text = "\n".join(text_parts).strip()
            logger.info(
                "PDF text extracted",
                extra={"path": str(path), "pages": len(text_parts), "chars": len(full_text)},
            )
            return full_text

        except Exception as exc:
            logger.error("PDF parsing failed", exc_info=exc, extra={"path": str(path)})
            raise InternalError(detail=f"Failed to parse PDF: {exc}") from exc

    def extract_text_from_docx(self, path: Path) -> str:
        """Extracts text from a DOCX file using python-docx."""
        try:
            extension = path.suffix.lower()
            if not extension == ".docx":
                raise UnsupportedFileTypeError(detail="File is not a DOCX")
            
            doc = docx.Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            full_text = "\n".join(paragraphs).strip()

            logger.info(
                "DOCX text extracted",
                extra={"path": str(path), "paragraphs": len(paragraphs), "chars": len(full_text)},
            )
            return full_text

        except Exception as exc:
            logger.error("DOCX parsing failed", exc_info=exc, extra={"path": str(path)})
            raise InternalError(detail=f"Failed to parse DOCX: {exc}") from exc

    def extract_text_from_txt(self, path: Path) -> str:
        """Extracts text from a TXT file."""
        try:
            extension = path.suffix.lower()
            if not extension == ".txt":
                raise UnsupportedFileTypeError(detail="File is not a TXT")
            
            full_text = path.read_text(encoding="utf-8")
            logger.info(
                "TXT text extracted",
                extra={"path": str(path), "chars": len(full_text)},
            )
            return full_text
        except Exception as exc:
            logger.error("TXT parsing failed", exc_info=exc, extra={"path": str(path)})
            raise InternalError(detail=f"Failed to parse TXT: {exc}") from exc