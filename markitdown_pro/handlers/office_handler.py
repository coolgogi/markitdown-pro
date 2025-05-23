from ..common.logger import logger
from ..common.utils import ensure_minimum_content
from ..converters.azure_docint import AzureDocIntWrapper
from ..converters.unstructured_wrapper import UnstructuredWrapper
from .base_handler import BaseHandler


class OfficeHandler(BaseHandler):
    extensions = frozenset([".doc", ".docx", ".odt", ".rtf", ".ppt", ".pptx"])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.azure_docint = AzureDocIntWrapper()
        self.unstructured = UnstructuredWrapper()

    async def handle(self, file_path, *args, **kwargs) -> str:
        """
        Handles Office documents (.doc, .docx, .odt, .rtf, .ppt, .pptx) by
        first trying Azure Document Intelligence and falling back to Unstructured.

        Args:
            file_path: Path to the Office document file.

        Returns:
            Markdown string representing the document content, or an error message.
        """
        logger.info(f"Processing Office document: {file_path}")
        try:
            # First try with Azure Document Intelligence
            logger.info(f"Attempting conversion with Azure Document Intelligence for: {file_path}")
            md_content = await self.azure_docint.convert(file_path)
            if md_content and ensure_minimum_content(md_content):
                return md_content

            # Fallback to Unstructured if Azure Doc Intelligence fails or returns insufficient content
            logger.info(f"Falling back to Unstructured for: {file_path}")
            md_content = await self.unstructured.convert(file_path)
            if md_content and ensure_minimum_content(md_content):
                return md_content

            raise RuntimeError(
                f"Office document conversion failed with both Azure Doc Intelligence and Unstructured: {file_path}"
            )

        except Exception as e:
            logger.error(f"Error handling Office document '{file_path}': {e}")
            return "# Error al procesar documento de Office"
