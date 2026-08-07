from app.core.config import settings
from pathlib import Path
from app.core.exceptions import InternalError, UnsupportedFileTypeError
from app.core.logging import get_logger
import docx
import io

try:
    import pymupdf
    from PIL import Image
    import pytesseract
    OCR_AVAILABLE=True
except ImportError:
    OCR_AVAILABLE=False


logger = get_logger(__name__)



class ExtractTextService:

    SUPPORTED_EXTENSIONS: tuple[str, ...] = (".pdf", ".docx", ".txt")

    def extract_text(self, path: Path) -> str:
        """
        Extracts text from a CV file, dispatching on its extension.

        Args:
            path: Path to the file to parse.

        Returns:
            The extracted plain text.

        Raises:
            UnsupportedFileTypeError: Extension is not one of SUPPORTED_EXTENSIONS.
            InternalError:            The file matched a supported type but could
                                      not be parsed (corrupted, unreadable...).
        """
        extension = path.suffix.lower()

        if extension == ".pdf":
            return self.extract_text_from_pdf(path)
        if extension == ".docx":
            return self.extract_text_from_docx(path)
        if extension == ".txt":
            return self.extract_text_from_txt(path)

        raise UnsupportedFileTypeError(
            detail=f"Unsupported file type: {extension or path.name}",
            context={"extension": extension, "supported": list(self.SUPPORTED_EXTENSIONS)},
        )

    def extract_text_from_pdf_ocr(self, path: Path) -> str:
        """Extracts text from a PDF file using OCR."""
        full_text=""
        try:
            if not OCR_AVAILABLE:
                raise InternalError(detail="OCR is not available run uv add pymupdf pytesseract pillow")
            
            extension = path.suffix.lower()
            if not extension == ".pdf":
                raise UnsupportedFileTypeError(detail="File is not a PDF")


            text_parts: list[str] = []

            doc = pymupdf.open(path)
            for page in doc:
                pix = page.get_pixmap(dpi=settings.ocr_dpi)
                img = Image.open(io.BytesIO(pix.tobytes(settings.ocr_image_bytes_format)))
                text = pytesseract.image_to_string(img)
                text_parts.append(text)
            doc.close()

            full_text = "\n".join(text_parts).strip()
            logger.info(
                "PDF Text extracted using OCR",
                extra={"path": str(path), "pages": len(text_parts), "chars": len(full_text)},
            )
            return full_text

        except Exception as exc:
            logger.error("PDF parsing failed", exc_info=exc)
            return full_text


    def extract_text_from_pdf(self, path: Path) -> str:
        """Extracts text from a PDF file using PyPDF2."""
        try:
            extension = path.suffix.lower()
            if not extension == ".pdf":
                raise UnsupportedFileTypeError(detail="File is not a PDF")

            text_parts: list[str] = []

            doc = pymupdf.open(path)
            for page in doc:
                text_parts.append(page.get_text())
            doc.close()

            full_text = "\n".join(text_parts).strip()

            # if the text is too short, try to extract it using OCR
            if len(full_text) < 50:
                full_text = self.extract_text_from_pdf_ocr(path)

            logger.info(
                "PDF text extracted",
                extra={"path": str(path), "pages": len(text_parts), "chars": len(full_text)},
            )
            return full_text

        except UnsupportedFileTypeError:
            # Domain error: keep the 415, don't downgrade it to a 500 below.
            raise
        except Exception as exc:
            logger.error("PDF parsing failed", exc_info=exc, extra={"path": str(path)})
            raise InternalError(detail=f"Failed to parse PDF: {exc}") from exc

    def extract_text_from_docx(self, path: Path) -> str:
        """Extracts text from a DOCX file using python-docx."""
        try:
            extension = path.suffix.lower()
            if not extension == ".docx":
                raise UnsupportedFileTypeError(detail="File is not a DOCX")
            
            full_text=""
            doc = docx.Document(str(path))
            parts = []

            # 1. Paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    parts.append(para.text)
            
            # 2. Tables
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        # get the text of each cell
                        cell_text = " | ".join(p.text for p in cell.paragraphs if p.text.strip())
                        if cell_text:
                            row_text.append(cell_text)
                    
                    if row_text:
                        parts.append(" | ".join(row_text))

            # 3. Headers & Footers
            for section in doc.sections:
                # Header
                for para in section.header.paragraphs:
                    if para.text.strip():
                        parts.append(f"[HEADER] {para.text}")
                
                # Footer
                for para in section.footer.paragraphs:
                    if para.text.strip():
                        parts.append(f"[FOOTER] {para.text}")

            # 4. Text in Shapes (text boxes, etc.)
            ns = "http://schemas.openxmlformats.org/drawingml/2006/main"
            for t in doc.element.body.iter(f"{{{ns}}}t"):
                if t.text and t.text.strip():
                    parts.append(t.text)

                    
            full_text = "\n".join(parts).strip()

            logger.info(
                "DOCX text extracted",
                extra={"path": str(path), "paragraphs": len(parts), "chars": len(full_text)},
            )
            return full_text

        except UnsupportedFileTypeError:
            raise
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
        except UnsupportedFileTypeError:
            raise
        except Exception as exc:
            logger.error("TXT parsing failed", exc_info=exc, extra={"path": str(path)})
            raise InternalError(detail=f"Failed to parse TXT: {exc}") from exc