from typing import Optional

from ..services.azure_service import AzureServices
from .base import ConverterWrapper


class AzureDocIntWrapper(ConverterWrapper):
    def __init__(self):
        super().__init__("Azure Document Intelligence")
        self.azure_services = AzureServices()

    async def convert(self, file_path: str) -> Optional[str]:
        return self.azure_services.process_azure_doc_intelligence(file_path)
