import logging
import os
from pathlib import Path
from typing import Optional

import azure.cognitiveservices.speech as speechsdk
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature
from azure.ai.documentintelligence.models import DocumentContentFormat as ContentFormat
from azure.core.credentials import AzureKeyCredential

from ..common.logger import logger
from ..common.utils import clean_markdown, ensure_minimum_content


class AzureServices:
    def __init__(self=None):
        self.azure_doc_client = None
        self.azure_speech_config = None
        self.azure_speech_voice_name = "en-US-AndrewMultilingualNeural"
        self._initialize_azure_services()

    def _initialize_azure_services(self):

        # Initialize Azure Document Intelligence client
        azure_docint_endpoint = os.getenv("AZURE_DOCINTEL_ENDPOINT", "")
        azure_docint_key = os.getenv("AZURE_DOCINTEL_KEY", "")
        if azure_docint_endpoint and azure_docint_key:
            try:
                self.azure_doc_client = DocumentIntelligenceClient(
                    endpoint=azure_docint_endpoint,
                    credential=AzureKeyCredential(azure_docint_key),
                )
            except Exception as e:
                logging.warning(f"Failed to initialize Azure Document Intelligence client: {e}")

        azure_speech_key = os.getenv("AZURE_SPEECH_KEY", "")
        azure_speech_region = os.getenv("AZURE_SPEECH_REGION", "")
        if azure_speech_key and azure_speech_region:
            try:
                self.azure_speech_config = speechsdk.SpeechConfig(
                    subscription=azure_speech_key, region=azure_speech_region
                )
            except Exception as e:
                logging.warning(f"Failed to initialize Azure Speech Service configuration: {e}")

    def process_azure_doc_intelligence(self, file_path: str) -> Optional[str]:
        """
        Convert a document to Markdown using Azure Document Intelligence.
        """
        if not self.azure_doc_client:
            logger.info("Azure Document Intelligence client not configured, skipping conversion.")
            return None

        logger.info(f"Attempting Azure Document Intelligence conversion on '{file_path}'")
        try:
            with open(file_path, "rb") as f:
                file_data = f.read()

            # Detect file extension
            extension = Path(file_path).suffix.lower()
            if extension not in [".docx", ".xlsx", ".pptx"]:
                features = [DocumentAnalysisFeature.LANGUAGES]
            else:
                features = []

            poller = self.azure_doc_client.begin_analyze_document(
                model_id="prebuilt-layout",
                body=file_data,
                content_type="application/octet-stream",
                features=features,
                output_content_format=ContentFormat.MARKDOWN,
            )
            result = poller.result(timeout=120)

            if hasattr(result, "content"):
                content = result.content or ""

            else:
                # Fallback for older API responses
                lines = []
                for page in result.pages:
                    for line in page.lines:
                        lines.append(line.content)
                content = "\n".join(lines)

            final_md = clean_markdown(content)
            if ensure_minimum_content(final_md):
                return final_md

            logger.info("Azure Document Intelligence conversion returned insufficient content.")
            return None

        except Exception as e:
            logger.error(f"Error during Azure Document Intelligence conversion: {e}")
            return None

    async def recognize_azure_speech_to_text_from_file(self, file_path: str) -> Optional[str]:
        """
        Recognize speech from an audio file with automatic language detection
        across the top 6 spoken languages globally.

        Args:
            file_path (str): Path to the audio file.

        Returns:
            Optional[str]: Transcribed text if successful, None otherwise.
        """
        if not self.azure_speech_config:
            logging.info("Azure Speech Service not configured, skipping speech recognition.")
            return None

        try:
            audio_config = speechsdk.AudioConfig(filename=file_path)
            languages = ["en-US", "zh-CN", "hi-IN", "es-ES"]

            # Configure auto language detection with the specified languages
            auto_detect_source_language_config = (
                speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=languages)
            )

            # Create a speech recognizer with the auto language detection configuration
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.azure_speech_config,
                audio_config=audio_config,
                auto_detect_source_language_config=auto_detect_source_language_config,
            )

            # Perform speech recognition
            result = await speech_recognizer.recognize_once_async()

            # Check the result
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                # Retrieve the detected language
                detected_language = result.properties.get(
                    speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult,
                    "Unknown",
                )
                logging.debug(f"Detected Language {detected_language}")
                return result.text

            elif result.reason == speechsdk.ResultReason.NoMatch:
                logging.warning("No speech could be recognized from the audio.")
                return None

            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speechsdk.CancellationDetails(result)
                logging.error(
                    f"Speech Recognition canceled: {cancellation_details.reason}. "
                    f"Error details: {cancellation_details.error_details}"
                )
                return None

            else:
                logging.error("Unknown error occurred during speech recognition.")
                return None

        except Exception as e:
            logging.error(f"An error occurred during speech recognition: {e}")
            return None
