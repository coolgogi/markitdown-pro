import logging
from typing import Optional

from markitdown import MarkItDown

from ..common.logger import logger
from ..common.utils import clean_markdown, ensure_minimum_content
from .base import ConverterWrapper


class MarkitDownWrapper(ConverterWrapper):
    SUPPORTED_FORMATS = [
        "txt",
        "md",
        "html",
        "pdf",
        "docx",
        "xlsx",
        "pptx",
        "zip",
        "wav",
        "mp3",
        "jpg",
        "png",
        "gif",
        "bmp",
        "tiff",
    ]

    def __init__(self):
        super().__init__("MarkItDown")
        self.markitdown = MarkItDown()

    async def convert(self, file_path: str) -> Optional[str]:
        file_extension = file_path.split(".")[-1].lower()
        logging.info(f"Processing MarkItDown file: {file_path} with extension: {file_extension}")

        if file_extension not in self.SUPPORTED_FORMATS:
            logger.warning(f"Unsupported file format: {file_extension}")
            return None

        result = self.markitdown.convert(file_path)
        text_md = clean_markdown(result.text_content or None)
        return text_md if ensure_minimum_content(text_md) else None
