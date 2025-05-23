from ..common.logger import logger
from ..converters.markitdown_wrapper import MarkitDownWrapper
from ..handlers.base_handler import BaseHandler
from ..services.azure_service import AzureServices


class AudioHandler(BaseHandler):
    extensions = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.markitdown = MarkitDownWrapper()
        self.azure_services = AzureServices()

    async def handle(self, file_path, *args, **kwargs) -> str:
        """
        Transcribe an audio file using MarkItDown first.
        If MarkItDown fails, fall back to Azure Speech-to-Text API.
        """
        logger.info(f"Processing audio file: {file_path} using MarkItDown")

        try:
            text: str = await self.markitdown.convert(file_path)
            if text:
                return text
            else:
                logger.warning(
                    "MarkItDown conversion returned insufficient content. Falling back to Azure Speech-to-Text API."
                )
        except Exception as e:
            logger.error(f"Error processing audio file with MarkItDown: {e}")

        # Fallback to Azure Speech-to-Text API
        try:
            logger.info(f"Transcribing audio file: {file_path} using Azure Speech-to-Text API")
            text = await self.azure_services.recognize_azure_speech_to_text_from_file(file_path)
            return text if text else "# Audio File\n\n(Transcription not available.)"
        except Exception as e:
            logger.error(f"Error transcribing audio file with Azure Speech-to-Text API: {e}")
            return "# Audio File\n\n(Transcription failed.)"
