import os
from typing import Optional

from .base_handler import BaseHandler

try:
    from libratom.lib.pff import PffArchive

    HAS_LIBRATOM = True
except ImportError:
    HAS_LIBRATOM = False

from ..common.logger import logger
from ..common.utils import clean_markdown, ensure_minimum_content


class PSTHandler(BaseHandler):
    extensions = frozenset([".pst"])

    async def handle(self, file_path, *args, **kwargs) -> str:
        """
        Parses a PST file using libratom, extracts messages and attachments,
        and converts the content to Markdown. Recursively processes attachments.

        Args:
            file_path: Path to the .pst file.

        Returns:
            Markdown string representing the PST content, or an error message.
        """
        if not HAS_LIBRATOM:
            logger.error("libratom is not installed. PST processing is disabled.")
            return "# Error: libratom not installed. Cannot process PST files."

        logger.info(f"Processing PST file: {file_path}")
        try:
            markdown_content = self._process_pst(file_path)
            if markdown_content:
                return markdown_content
            else:
                return "# PST Archive\n\n(No messages found or insufficient content.)"
        except Exception as e:
            logger.error(f"Error processing PST file: {file_path}: {e}")
            return f"# Error processing PST file: {e}"

    def _process_pst(self, file_path: str) -> Optional[str]:
        """
        Parses the PST file, extracts messages and attachments, and converts to Markdown.

        Args:
            file_path: Path to the PST file.

        Returns:
            Markdown string, or None if no messages are found or content is insufficient.
        """
        if not os.path.isfile(file_path):
            logger.error(f"PST file not found: {file_path}")
            return None

        all_md_parts = [f"# PST Archive: {os.path.basename(file_path)}\n"]

        try:
            with PffArchive(file_path) as archive:
                for folder in archive.folders():
                    if not folder.name:  # Skip folders with no name
                        continue

                    # Add folder information, handling None folder names
                    all_md_parts.append(f"\n## Folder: {folder.name or '(Unnamed Folder)'}\n")
                    message_count = 0

                    for message in folder.messages():
                        message_count += 1
                        try:
                            message_md = self._process_message(message, message_count)
                            if message_md:
                                all_md_parts.extend(message_md)
                        except Exception as e:
                            logger.error(
                                f"Error processing message {message_count} in folder {folder.name}: {e}"
                            )
                            all_md_parts.append(
                                f"### Error processing message {message_count}: {e}"
                            )

            final_md = clean_markdown("\n\n".join(all_md_parts))
            return final_md if ensure_minimum_content(final_md) else None

        except Exception as e:
            logger.error(f"Error opening or processing PST archive {file_path}: {e}")
            return None

    def _process_message(self, message, message_count: int) -> Optional[list[str]]:
        """
        Processes a single message from the PST archive.

        Args:
            message: The message object from libratom.
            message_count:  The message number within the folder (for display).

        Returns:
            A list of Markdown strings representing the message, or None on error.
        """
        try:
            subject = message.subject or "(No Subject)"
            sender = "Unknown Sender"
            date_ = "Unknown Date"

            # Extract headers safely, handling potential errors
            try:
                headers = message.transport_headers
                if headers:
                    if isinstance(headers, bytes):
                        headers = headers.decode(errors="replace")
                    for line in headers.splitlines():
                        if line.lower().startswith("from:"):
                            sender = line.split(":", 1)[1].strip()
                        elif line.lower().startswith("date:"):
                            date_ = line.split(":", 1)[1].strip()
            except Exception as header_err:
                logger.warning(f"Error parsing headers: {header_err}")

            # Extract the body, handling different encodings and body types
            body_content = ""
            try:
                if message.plain_text_body:
                    body_content = message.plain_text_body.decode(errors="replace")
                elif message.html_body:
                    body_content = message.html_body.decode(errors="replace")
                elif message.rtf_body:
                    body_content = message.rtf_body.decode(errors="replace")

            except Exception as body_err:
                logger.warning(f"Error decoding message body: {body_err}")

            message_md_parts = [
                f"### Message {message_count}",
                f"**Subject:** {subject}",
                f"**From:** {sender}",
                f"**Date:** {date_}",
                "",
                "```",
                body_content.strip() if body_content else "[No body text]",
                "```",
            ]

            # Handle attachments todo: handle attachments

            return message_md_parts

        except Exception as e:
            logger.error(f"Error processing individual message: {e}")
            return None
