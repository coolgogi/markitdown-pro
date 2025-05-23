from typing import Optional
from urllib.parse import parse_qs, urlparse

from markitdown import MarkItDown
from youtube_transcript_api import YouTubeTranscriptApi

from ..common.logger import logger
from .base import ConverterWrapper


class YouTubeWrapper(ConverterWrapper):
    def __init__(self):
        super().__init__("YouTube")
        self.markitdown = MarkItDown()

    async def convert(self, url: str) -> Optional[str]:
        logger.info(f"Processing YouTube video: {url}")

        markitdown_result = self.markitdown.convert(url)
        markitdown_content = markitdown_result.text_content if markitdown_result else None

        if not markitdown_content:
            logger.warning("MarkItDown processing failed or returned empty content.")

        parsed_url = urlparse(url)
        params = parse_qs(parsed_url.query)
        if "v" not in params:
            logger.warning(f"Invalid YouTube URL: {url}")
            return markitdown_content

        video_id = params["v"][0]
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript_text = None

            for lang in [
                "en",
                "es",
                "fr",
                "de",
                "it",
                "pt",
                "ru",
                "zh-Hans",
                "ja",
                "ko",
            ]:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    transcript_text = "\n".join([part["text"] for part in transcript.fetch()])
                except Exception as e:
                    logger.info(f"No transcript found for language {lang}: {e}")
                    continue

            if not transcript_text:
                logger.warning(f"No transcript found for YouTube video: {url}")
                return markitdown_content
            full_content = (
                f"{markitdown_content}\n\n# YouTube Transcript\n\n{transcript_text}"
                if markitdown_content
                else f"# YouTube Transcript\n\n{transcript_text}"
            )
            return full_content

        except Exception as e:
            logger.error(f"Error fetching transcript for YouTube video {url}: {e}", exc_info=True)
            return markitdown_content
