from typing import Optional

from ..common.utils import is_pdf
from ..services.openai_services import GPT4oMiniVision
from .base import ConverterWrapper


class GPT4oMiniVisionWrapper(ConverterWrapper):
    def __init__(self):
        super().__init__("GPT-4o-mini Vision")
        self.gpt4o_mini = GPT4oMiniVision()  # Instantiate the actual service

    async def convert(self, file_path: str) -> Optional[str]:
        if is_pdf(file_path):
            # Try concurrent first, then simple if it fails
            result = await self.gpt4o_mini.process_scanned_pdf_concurrent(file_path)
            if result:
                return result
            return await self.gpt4o_mini.process_scanned_pdf_simple(file_path)
        else:  # Assume it's an image
            return await self.gpt4o_mini.process_image(file_path)
