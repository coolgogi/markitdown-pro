from typing import Optional

from ..common.logger import logger


class ConverterWrapper:
    SUPPORTED_FORMATS = ()

    def __init__(self, name: str):
        self.name = name

    async def convert(self, file_path: str) -> Optional[str]:  # MUST be async
        raise NotImplementedError("Subclasses must implement this method.")

    async def process(self, file_path: str) -> Optional[str]:  # Make process async
        logger.info(f"Processing {self.name} for file: {file_path}")
        try:
            result = await self.convert(file_path)  # AWAIT the convert
            if result:
                return result
            else:
                logger.warning(f"{self.name} conversion returned insufficient content.")
                return None
        except Exception as e:
            logger.error(f"Error during {self.name} conversion: {e}")
            return None
