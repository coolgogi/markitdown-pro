from typing import Optional

from unstructured.partition.auto import partition

from ..common.logger import logger
from ..common.utils import clean_markdown, ensure_minimum_content
from .base import ConverterWrapper


class UnstructuredWrapper(ConverterWrapper):
    SUPPORTED_FORMATS = (
        "txt",
        "md",
        "html",
        "htm",
        "xml",
        "pdf",
        "docx",
        "xlsx",
        "pptx",
        "odt",
        "ods",
        "odp",
        "rtf",
        "json",
        "csv",
        "tsv",
        "jpg",
        "jpeg",
        "png",
        "gif",
        "bmp",
        "tiff",
        "svg",
        "mp3",
        "wav",
        "ogg",
        "flac",
        "zip",
        "tar",
        "gz",
        "rar",
        "epub",
        "eml",
        "msg",
    )

    def __init__(self):
        super().__init__("Unstructured")

    async def convert(self, file_path: str) -> Optional[str]:
        logger.debug(f"Converting {file_path} to markdown")
        file_extension = file_path.split(".")[-1].lower()

        if file_extension not in self.SUPPORTED_FORMATS:
            logger.warning(f"Unsupported file format: {file_extension}")
            return None

        # Directly call partition.  No asyncio.to_thread
        elements = partition(filename=file_path, extract_images_in_pdf=True)
        combined = clean_markdown("\n\n".join(str(el) for el in elements))
        return combined if ensure_minimum_content(combined) else None
