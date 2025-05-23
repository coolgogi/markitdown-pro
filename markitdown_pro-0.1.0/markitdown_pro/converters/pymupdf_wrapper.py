import logging
from typing import Optional

import fitz  # PyMuPDF

from ..common.logger import logger
from ..common.utils import clean_markdown, ensure_minimum_content
from .base import ConverterWrapper


class PyMuPDFWrapper(ConverterWrapper):
    SUPPORTED_FORMATS = ["pdf", "xps", "epub", "mobi", "fb2", "cbz", "svg"]

    def __init__(self):
        super().__init__("PyMuPDF")

    async def convert(self, file_path: str) -> Optional[str]:
        file_extension = file_path.split(".")[-1].lower()
        logging.info(f"Processing PyMuPDF file: {file_path} with extension: {file_extension}")

        if file_extension not in self.SUPPORTED_FORMATS:
            logger.warning(f"Unsupported file format: {file_extension}")
            return None

        try:
            doc = fitz.open(file_path)

            # Extract text from all pages
            text_content = ""
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                text_content += page.get_text()
                text_content += "\n\n"

            doc.close()

            text_md = clean_markdown(text_content)
            return text_md if ensure_minimum_content(text_md) else None

        except Exception as e:
            logger.error(f"Error processing document with PyMuPDF: {e}")
            return None
