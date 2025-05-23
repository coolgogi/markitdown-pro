import os
import tempfile
from pathlib import Path
from typing import Optional

import requests

from .common.logger import logger
from .common.utils import detect_extension, ensure_minimum_content, is_image
from .converters.azure_docint import AzureDocIntWrapper
from .converters.gpt4o_mini_vision import GPT4oMiniVisionWrapper
from .converters.markitdown_wrapper import MarkitDownWrapper
from .converters.unstructured_wrapper import UnstructuredWrapper
from .handlers.audio_handler import AudioHandler
from .handlers.base_handler import BaseHandler  # Import BaseHandler
from .handlers.email_handler import EmailHandler
from .handlers.epub_handler import EPUBHandler
from .handlers.image_handler import ImageHandler
from .handlers.ipynb_handler import IpynbHandler
from .handlers.markup_handler import MarkupHandler
from .handlers.office_handler import OfficeHandler
from .handlers.pdf_handler import PDFHandler
from .handlers.pst_handler import PSTHandler
from .handlers.tabular_handler import TabularHandler
from .handlers.text_handler import TextHandler


def _write_md(path: str, content: str) -> str:
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return content


class ConversionPipeline:
    """
    A class to encapsulate the conversion pipeline, making it easier to use
    without needing to directly interact with dependency injection in the main
    functions.  This simplifies testing and usage.
    """

    def __init__(
        self,
    ):
        self.pdf_handler = PDFHandler()
        self.audio_handler = AudioHandler()
        self.image_handler = ImageHandler()
        self.text_handler = TextHandler()
        self.tabular_handler = TabularHandler()
        self.markup_handler = MarkupHandler()
        self.office_handler = OfficeHandler()
        self.epub_handler = EPUBHandler()
        self.email_handler = EmailHandler()
        self.pst_handler = PSTHandler()
        self.ipynb_handler = IpynbHandler()
        self.markitdown_wrapper = MarkitDownWrapper()
        self.unstructured_wrapper = UnstructuredWrapper()
        self.azure_docint_wrapper = AzureDocIntWrapper()
        self.gpt4o_mini_vision_wrapper = GPT4oMiniVisionWrapper()

        # Define the handlers in a dictionary mapping extensions to handlers
        self.handlers_mapping: dict[str, BaseHandler] = {  # Use BaseHandler type hint
            ".pdf": self.pdf_handler,
            ".mp3": self.audio_handler,
            ".wav": self.audio_handler,
            ".ogg": self.audio_handler,
            ".flac": self.audio_handler,
            ".m4a": self.audio_handler,
            ".aac": self.audio_handler,
            ".wma": self.audio_handler,
            ".webm": self.audio_handler,
            ".opus": self.audio_handler,
            ".bmp": self.image_handler,
            ".gif": self.image_handler,
            ".heic": self.image_handler,
            ".jpeg": self.image_handler,
            ".jpg": self.image_handler,
            ".png": self.image_handler,
            ".prn": self.image_handler,
            ".svg": self.image_handler,
            ".tiff": self.image_handler,
            ".webp": self.image_handler,
            ".heif": self.image_handler,
            ".txt": self.text_handler,
            ".md": self.text_handler,
            ".py": self.text_handler,
            ".go": self.text_handler,
            ".csv": self.tabular_handler,
            ".tsv": self.tabular_handler,
            ".xls": self.tabular_handler,
            ".xlsx": self.tabular_handler,
            ".html": self.markup_handler,
            ".htm": self.markup_handler,
            ".xml": self.markup_handler,
            ".json": self.markup_handler,
            ".ndjson": self.markup_handler,
            ".yaml": self.markup_handler,
            ".yml": self.markup_handler,
            ".doc": self.office_handler,
            ".docx": self.office_handler,
            ".odt": self.office_handler,
            ".rtf": self.office_handler,
            ".ppt": self.office_handler,
            ".pptx": self.office_handler,
            ".epub": self.epub_handler,
            ".eml": self.email_handler,
            ".p7s": self.email_handler,
            ".msg": self.email_handler,
            ".pst": self.pst_handler,
            ".ipynb": self.ipynb_handler,
        }

    async def convert_document_to_md(self, file_path: str, output_md: Optional[str] = None) -> str:
        """
        Convert a document to Markdown by trying a series of specialized handlers.
        """
        if not Path(file_path).is_file():
            raise ValueError(f"The provided path '{file_path}' is not a valid file.")

        if not output_md:
            base = os.path.splitext(file_path)[0]
            output_md = base + ".md"

        logger.debug(f"convert_document_to_md: Converting '{file_path}' --> '{output_md}'")

        extension = detect_extension(file_path).lower()

        handler = self.handlers_mapping.get(extension)

        if handler:
            try:
                logger.debug(f"convert_document_to_md: Using handler for extension '{extension}'")
                md_content = await handler.handle(file_path)  # AWAIT the handler!
                if not md_content:
                    raise RuntimeError(f"Handler for {extension} returned None for {file_path}")

                logger.debug(
                    f"convert_document_to_md: Handler returned {len(md_content)} characters"
                )
                if md_content and ensure_minimum_content(md_content):
                    return _write_md(output_md, md_content)
                else:
                    raise RuntimeError(
                        f"Conversion failed for {file_path} using handler for {extension}"
                    )
            except Exception as e:
                logger.error(f"Error in handler for extension {extension}: {e}")
                raise

        else:
            logger.warning(f"No specific handler found for '{extension}'. Using default path.")
            # Use the injected wrappers directly
            md_out = await self.markitdown_wrapper.process(file_path)
            if md_out and ensure_minimum_content(md_out):
                return _write_md(output_md, md_out)
            md_out = await self.unstructured_wrapper.process(file_path)
            if md_out and ensure_minimum_content(md_out):
                return _write_md(output_md, md_out)
            md_out = await self.azure_docint_wrapper.process(file_path)
            if md_out and ensure_minimum_content(md_out):
                return _write_md(output_md, md_out)
            if is_image(file_path):
                md_out = await self.gpt4o_mini_vision_wrapper.process(file_path)
                if md_out and ensure_minimum_content(md_out):
                    return _write_md(output_md, md_out)

            raise RuntimeError(f"Markdown conversion failed for {file_path} at the default path.")

    async def convert_document_from_url(
        self, url: str, output_md: Optional[str] = None
    ) -> str:  # Add async
        logger.info(f"convert_document_from_url: Downloading '{url}'")
        resp = requests.get(url, stream=True)  # requests is *synchronous*
        resp.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".download") as tmp:
            for chunk in resp.iter_content(chunk_size=8192):
                tmp.write(chunk)
            tmp.flush()
            local_path = tmp.name

        try:
            return await self.convert_document_to_md(
                local_path, output_md=output_md
            )  # Await the call
        finally:
            Path(local_path).unlink(missing_ok=True)

    async def convert_document_from_stream(
        self, stream, extension: str, output_md: Optional[str] = None
    ) -> str:  # Add async
        if not extension.startswith("."):
            extension = "." + extension
        logger.debug(
            f"convert_document_from_url: Converting from stream with extension '{extension}'"
        )

        from io import BytesIO

        if not isinstance(stream, BytesIO):
            raise ValueError("Stream must be a BytesIO object")

        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as tmp:
            tmp.write(stream.read())
            tmp.flush()
            local_path = tmp.name

        try:
            return await self.convert_document_to_md(
                local_path, output_md=output_md
            )  # Await the call
        finally:
            Path(local_path).unlink(missing_ok=True)
