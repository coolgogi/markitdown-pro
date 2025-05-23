from ..common.logger import logger
from ..common.utils import ensure_minimum_content
from ..converters.unstructured_wrapper import UnstructuredWrapper
from .base_handler import BaseHandler


class EPUBHandler(BaseHandler):
    extensions = frozenset([".epub"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.unstructured = UnstructuredWrapper()

    async def handle(self, file_path, *args, **kwargs) -> str:
        """
        Handles EPUB files by converting them to Markdown using Unstructured.

        Args:
            file_path: Path to the .epub file.

        Returns:
            Markdown string representing the EPUB content, or an error message.
        """
        logger.info(f"Processing EPUB file {file_path}")
        try:
            md_content = await self.unstructured.convert(file_path)  # added await
            if md_content and ensure_minimum_content(md_content):
                return md_content
            else:
                raise RuntimeError(f"EPUB conversion failed or insufficient content: {file_path}")
        except Exception as e:
            logger.error(f"Error handling EPUB file '{file_path}': {e}")
            return "# Error al procesar EPUB"
