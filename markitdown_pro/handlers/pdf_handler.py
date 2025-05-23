from enum import Enum

import fitz

from ..common.logger import logger
from ..common.utils import ensure_minimum_content
from ..converters.azure_docint import AzureDocIntWrapper
from ..converters.gpt4o_mini_vision import GPT4oMiniVisionWrapper
from ..converters.markitdown_wrapper import MarkitDownWrapper
from ..converters.pymupdf_wrapper import PyMuPDFWrapper
from ..converters.unstructured_wrapper import UnstructuredWrapper
from .base_handler import BaseHandler


class PDFType(Enum):
    """
    Tipos de PDF detectados por el PDFHandler.

    - TEXT_ONLY:       PDF que contiene solo texto, sin imágenes.
    - TEXT_PLUS_IMAGES: PDF que contiene texto e imágenes.
    - ALL_IMAGES:      PDF que contiene solo imágenes (PDF escaneado).
    """

    TEXT_ONLY = "TEXT_ONLY"
    TEXT_PLUS_IMAGES = "TEXT_PLUS_IMAGES"
    ALL_IMAGES = "ALL_IMAGES"


class PDFHandler(BaseHandler):
    extensions = frozenset([".pdf"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.markitdown = MarkitDownWrapper()
        self.unstructured = UnstructuredWrapper()
        self.azure_docint = AzureDocIntWrapper()
        self.gpt4o_mini_vision = GPT4oMiniVisionWrapper()
        self.pymu = PyMuPDFWrapper()

        self.text_pipeline = [
            self.markitdown,
            self.unstructured,
            self.pymu,
            self.azure_docint,
        ]
        self.image_pipeline = [
            self.gpt4o_mini_vision,
        ]

    async def handle(self, file_path, *args, **kwargs):
        try:
            pdf_type = await self._detect_pdf_type(file_path)

            if pdf_type == PDFType.TEXT_ONLY:
                pipeline = self.text_pipeline
            elif pdf_type == PDFType.ALL_IMAGES:
                pipeline = self.image_pipeline
            elif pdf_type == PDFType.TEXT_PLUS_IMAGES:
                pipeline = self.text_pipeline + self.image_pipeline
            else:
                pipeline = self.text_pipeline

            for converter in pipeline:
                logger.info(f"Trying {converter.name} for PDF {file_path}")
                try:
                    md_content = await converter.convert(file_path)
                    if md_content and ensure_minimum_content(md_content):
                        return md_content
                except Exception as e:
                    logger.error(f"Converter {converter.name} failed for PDF {file_path}: {e}")

            raise RuntimeError(f"PDF conversion failed with all converters for {file_path}")

        except Exception as e:
            logger.error(f"Error handling PDF '{file_path}': {e}")
            return None

    async def _detect_pdf_type(self, file_path: str) -> PDFType:
        """
        Detect the type of PDF file based on its content.
        """
        min_text_length_threshold = 50

        try:

            async def open_and_process_doc():
                with fitz.open(file_path) as doc:
                    total_pages = doc.page_count
                    pages_with_text = 0
                    pages_with_images = 0

                    for page_index in range(total_pages):
                        page = doc.load_page(page_index)
                        page_text = page.get_text().strip()
                        if len(page_text) >= min_text_length_threshold:
                            pages_with_text += 1
                        images = page.get_images(full=True)
                        if images:
                            pages_with_images += 1

                    logger.debug(f"Pages with text: {pages_with_text}/{total_pages}")
                    logger.debug(f"Pages with images: {pages_with_images}/{total_pages}")

                    is_text_only = pages_with_text == total_pages and pages_with_images == 0
                    is_all_images = pages_with_images == total_pages and pages_with_text == 0
                    has_text_and_images = pages_with_text > 0 and pages_with_images > 0

                    if is_text_only:
                        return PDFType.TEXT_ONLY
                    elif is_all_images:
                        return PDFType.ALL_IMAGES
                    elif has_text_and_images:
                        return PDFType.TEXT_PLUS_IMAGES
                    else:
                        return PDFType.TEXT_PLUS_IMAGES  # Fallback

            return await open_and_process_doc()  # Run in thread
        except Exception as e:
            logger.error(f"Error analyzing PDF '{file_path}': {e}")
            #  Important to re-raise the exception after logging, so the
            #  caller knows something went wrong *during the analysis*.
            raise
