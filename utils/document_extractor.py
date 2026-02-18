"""
Utility to extract text content from various document formats.
Supports: .md, .txt, .docx, .pdf
"""
from pathlib import Path
from typing import Union
import io


class DocumentExtractor:
    """Extract text content from various document formats"""

    @staticmethod
    def extract_text(file_content: bytes, filename: str) -> str:
        """
        Extract text from a file based on its extension.

        Args:
            file_content: Raw bytes of the file
            filename: Name of the file (used to determine extension)

        Returns:
            Extracted text content

        Raises:
            ValueError: If file format is not supported
        """
        extension = Path(filename).suffix.lower()

        if extension in ['.md', '.txt']:
            return DocumentExtractor._extract_text_plain(file_content)
        elif extension == '.docx':
            return DocumentExtractor._extract_text_docx(file_content)
        elif extension == '.pdf':
            return DocumentExtractor._extract_text_pdf(file_content)
        else:
            raise ValueError(f"Unsupported file format: {extension}")

    @staticmethod
    def _extract_text_plain(file_content: bytes) -> str:
        """Extract text from plain text files (.md, .txt)"""
        try:
            # Try UTF-8 first
            return file_content.decode('utf-8')
        except UnicodeDecodeError:
            # Fallback to latin-1
            return file_content.decode('latin-1')

    @staticmethod
    def _extract_text_docx(file_content: bytes) -> str:
        """Extract text from Word documents (.docx)"""
        try:
            from docx import Document
        except ImportError:
            raise ImportError(
                "python-docx is required for .docx files. "
                "Install with: pip install python-docx"
            )

        doc = Document(io.BytesIO(file_content))
        paragraphs = [paragraph.text for paragraph in doc.paragraphs]
        return '\n'.join(paragraphs)

    @staticmethod
    def _extract_text_pdf(file_content: bytes) -> str:
        """Extract text from PDF files (.pdf)"""
        try:
            import PyPDF2
        except ImportError:
            raise ImportError(
                "PyPDF2 is required for .pdf files. "
                "Install with: pip install PyPDF2"
            )

        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
        text_parts = []

        for page in pdf_reader.pages:
            text_parts.append(page.extract_text())

        return '\n'.join(text_parts)
