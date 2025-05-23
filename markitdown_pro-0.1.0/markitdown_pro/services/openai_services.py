import asyncio
import base64

# import concurrent.futures
import mimetypes
import os
import re
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import fitz
from langchain_core.messages import HumanMessage
from langchain_openai import AzureChatOpenAI
from PIL import Image as PILImage

from ..common.logger import logger
from ..common.utils import clean_markdown, ensure_minimum_content


class GPT4oMiniVision:
    def __init__(self=None):
        azure_key = os.getenv("AZURE_OPENAI_API_KEY")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")

        GPT4OMINI_DEPLOYMENT_NAME: str = os.getenv("GPT4oMINI_DEPLOYMENT_NAME", "")
        COMPLETION_TOKENS: int = 4096

        self.client = None
        if GPT4OMINI_DEPLOYMENT_NAME:
            try:
                from pydantic import BaseModel

                class ImageSchema(BaseModel):
                    ocr: str
                    analysis: str

                llm = AzureChatOpenAI(
                    deployment_name=GPT4OMINI_DEPLOYMENT_NAME,
                    temperature=0,
                    max_tokens=COMPLETION_TOKENS,
                    streaming=False,
                    api_version=api_version,
                    api_key=azure_key,
                    cache=False,
                )
                self.client = llm.with_structured_output(ImageSchema)
                logger.info("GPT-4o-mini client initialized successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize GPT-4o-mini client: {e}")
                self.client = None

    def _build_image_url_block(self, file_or_url: str) -> dict:
        if isinstance(file_or_url, Path):
            file_or_url = str(file_or_url)

        # If the input is a URL, return it as an image_url block
        if re.match(r"^https?://", file_or_url, re.IGNORECASE):
            return {
                "type": "image_url",
                "image_url": {"url": file_or_url},
            }

        path = Path(file_or_url)
        if not path.is_file():
            raise ValueError(f"Local file not found: {file_or_url}")

        try:
            content_type, _ = mimetypes.guess_type(file_or_url)
            if not content_type:
                content_type = "image/jpeg"
                logger.warning(
                    f"Could not determine content type for {file_or_url}, defaulting to image/jpeg"
                )

            # Convert the image to JPEG and encode it in Base64
            img = PILImage.open(file_or_url)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp_file:
                img.convert("RGB").save(tmp_file.name, "JPEG")
                jpeg_path = tmp_file.name

            with open(jpeg_path, "rb") as f:
                b64_data = base64.b64encode(f.read()).decode("utf-8")

            os.unlink(jpeg_path)  # Delete the temporary JPEG file

            return {
                "type": "image_url",
                "image_url": {"url": f"data:{content_type};base64,{b64_data}"},
            }
        except Exception as e:
            logger.error(f"Error building image block for {file_or_url}: {e}")
            raise

    async def process_image(self, file_or_url: str, prompt: Optional[str] = None) -> Optional[str]:
        if not prompt:
            prompt = (
                "Perform accurate OCR: answer with the markdown of the content of the image. Visually appealing markdown, nothing else. "
                "Perform Image Analysis: answer with a two line image analysis explaining what you see."
            )

        try:
            image_block = self._build_image_url_block(file_or_url)
            message_content = [
                {"type": "text", "text": prompt},
                image_block,
            ]
            message = HumanMessage(content=message_content)
            response = self.client.invoke([message])
            md_content = clean_markdown(response.analysis)
            md_content += "\n\n" + clean_markdown(response.ocr)

            return md_content if ensure_minimum_content(md_content) else None
        except Exception as e:
            logger.error(f"process_image: Error during GPT-4o-mini image OCR: {e}")
            return None

    async def process_scanned_pdf_concurrent(self, file_path: str) -> Optional[str]:
        if not self.client:
            return None

        try:
            doc = fitz.open(file_path)
            num_pages = doc.page_count
            results = []

            async def ocr_page(page_index: int) -> Tuple[int, str]:
                try:
                    page = doc.load_page(page_index)
                    pix = page.get_pixmap(dpi=150)

                    fd, png_path = tempfile.mkstemp(prefix=f"{page_index:3}-", suffix=".png")
                    os.close(fd)
                    pix.save(png_path)

                    try:
                        file_name = os.path.basename(file_path)
                        partial_md = await self.process_image(png_path)
                        if partial_md:
                            logger.debug(
                                f"ocr_page: {file_name} - page {page_index}: returned {len(partial_md)} characters"
                            )
                        else:
                            logger.warning(
                                f"ocr_page: {file_name} - page {page_index}: no OCR result"
                            )
                            partial_md = "[No OCR result]"
                        return (page_index, f"## Page {page_index + 1}\n\n{partial_md}")
                    finally:
                        try:
                            if os.path.exists(png_path):
                                # Remove the temporary PNG file after processing
                                logger.debug(f"Removing temporary PNG file: {png_path}")
                                Path(png_path).unlink(missing_ok=True)
                        except Exception as e:
                            logger.error(f"ocr_page: Error removing temporary PNG file: {e}")
                except Exception as e:
                    logger.error(f"ocr_page: Error processing page {page_index}: {e}")
                    return (page_index, None)

            logger.info(
                f"process_scanned_pdf_concurrent: Starting concurrent GPT-4o-mini OCR on PDF: '{file_path}'"
            )

            # run tasks concurrently
            tasks = [ocr_page(i) for i in range(num_pages)]
            results = await asyncio.gather(*tasks)

            combined_md = clean_markdown("\n\n".join(block for _, block in results))
            return combined_md if ensure_minimum_content(combined_md) else None

        except Exception as e:
            logger.error(f"Concurrent GPT-4o-mini OCR error for PDF {file_path}: {e}")
            return None

    async def process_scanned_pdf_simple(self, file_path: str) -> Optional[str]:
        if not self.client:
            return None

        try:
            doc = fitz.open(file_path)
            all_md_blocks = []

            logger.info(f"Starting simple GPT-4o-mini OCR on PDF: '{file_path}'")
            for i in range(doc.page_count):
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=150)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                    png_path = tmp_file.name
                    pix.save(png_path)
                try:
                    partial_md = await self.process_image(png_path)
                    if partial_md:
                        block = f"## Page {i + 1}\n\n{partial_md}"
                    else:
                        block = f"## Page {i + 1}\n\n[No OCR result]"
                    all_md_blocks.append(block)
                finally:
                    try:
                        Path(png_path).unlink(missing_ok=True)
                    except Exception as e:
                        logger.error(f"Error removing temporary PNG file in simple OCR: {e}")

            combined_md = clean_markdown("\n\n".join(all_md_blocks))
            return combined_md if ensure_minimum_content(combined_md) else None

        except Exception as e:
            logger.error(f"Simple GPT-4o-mini OCR error for PDF {file_path}: {e}")
            return None
