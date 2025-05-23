import os
import tempfile
from email.message import Message
from email.parser import BytesParser
from email.policy import default
from typing import Dict, List, Tuple

from ..common.logger import logger
from ..common.utils import clean_markdown
from .base_handler import BaseHandler


class EmailHandler(BaseHandler):
    extensions = frozenset([".eml", ".p7s"])

    async def handle(self, file_path, *args, **kwargs) -> str:
        logger.info(f"Processing email file: {file_path}")

        try:
            email_data = self._parse_email(file_path)
            if not email_data:
                return "# Error: Could not parse email file."

            markdown_content = self._build_markdown(email_data)
            return markdown_content

        except Exception as e:
            logger.error(f"Error processing email file: {file_path}: {e}")
            return f"# Error processing email: {e}"

    def _parse_email(self, file_path: str) -> Dict[str, any]:
        """
        Parses the EML/P7S file and extracts relevant information.

        Args:
            file_path: The path to the email file.

        Returns:
            A dictionary containing extracted data:
            {
                "subject": str,
                "from": str,
                "to": str,
                "date": str,
                "body": str,  # Plain text or HTML body (plain text preferred)
                "attachments": List[Tuple[str, str]],  # (filename, temp_file_path)
            }
            Returns an empty dictionary if parsing fails.
        """
        try:
            with open(file_path, "rb") as f:
                # Use BytesParser with the 'default' policy for best compatibility
                msg: Message = BytesParser(policy=default).parse(f)

            subject = msg.get("Subject", "(No Subject)")
            from_ = msg.get("From", "(Unknown Sender)")
            to_ = msg.get("To", "(Unknown Recipient)")
            date_ = msg.get("Date", "(Unknown Date)")

            body = ""
            attachments: List[Tuple[str, str]] = []

            # Prefer plain text body
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if part.get_content_disposition() == "attachment":
                        filename = part.get_filename()
                        if filename:
                            att_data = part.get_payload(decode=True)
                            # Create a temporary file for the attachment
                            with tempfile.NamedTemporaryFile(
                                delete=False, suffix=os.path.splitext(filename)[1]
                            ) as tmp_file:
                                tmp_file.write(att_data)
                            attachments.append((filename, tmp_file.name))

                    elif content_type == "text/plain" and not body:
                        # Get the charset, default to utf-8 if not specified
                        charset = part.get_content_charset() or "utf-8"
                        try:
                            body = part.get_payload(decode=True).decode(charset, errors="replace")
                        except Exception as decode_err:
                            logger.warning(
                                f"Error decoding text/plain part: {decode_err}, using fallback",
                            )
                            body = part.get_payload(decode=True).decode("utf-8", errors="replace")

                # If no plain text, try for HTML
                if not body:
                    for part in msg.walk():
                        if part.get_content_type() == "text/html":
                            charset = part.get_content_charset() or "utf-8"
                            try:
                                body = part.get_payload(decode=True).decode(
                                    charset, errors="replace"
                                )
                                break  # Stop after finding the first HTML part
                            except Exception as decode_err:
                                logger.warning(
                                    f"Error decoding text/html part: {decode_err}, using fallback",
                                )
                                body = part.get_payload(decode=True).decode(
                                    "utf-8", errors="replace"
                                )

            else:  # Not multipart
                content_type = msg.get_content_type()
                if content_type == "text/plain":
                    charset = msg.get_content_charset() or "utf-8"
                    body = msg.get_payload(decode=True).decode(charset, "replace")

                elif content_type == "text/html":
                    charset = msg.get_content_charset() or "utf-8"
                    body = msg.get_payload(decode=True).decode(charset, errors="replace")

            return {
                "subject": subject,
                "from": from_,
                "to": to_,
                "date": date_,
                "body": body,
                "attachments": attachments,
            }
        except Exception as e:
            logger.error(f"Error parsing email {file_path}: {e}")
            return {}

    def _build_markdown(self, email_data: Dict[str, any]) -> str:
        """
        Builds the Markdown output from the extracted email data.

        Args:
            email_data: The dictionary returned by _parse_email.

        Returns:
            The complete Markdown string.
        """
        # Use an f-string for more concise header formatting
        markdown_parts = [
            f"# Email: {email_data['subject']}",
            f"**From:** {email_data['from']}",
            f"**To:** {email_data['to']}",
            f"**Date:** {email_data['date']}",
            "",  # Add an empty line for separation
        ]

        body_content = email_data["body"]
        if body_content:
            markdown_parts.append("```")
            markdown_parts.append(body_content)  # Add the email body
            markdown_parts.append("```")

        for filename, filepath in email_data["attachments"]:
            markdown_parts.append(f"\n## Attachment: {filename}\n")
            try:
                # todo
                attachment_markdown = None
                markdown_parts.append(attachment_markdown)
            except Exception as e:
                logger.error(f"Error converting attachment '{filename}' in email: {e}")
                markdown_parts.append(f"[Error converting attachment: {e}]")
            finally:
                try:
                    os.remove(filepath)  # Clean up the temporary attachment file
                except OSError as e:
                    logger.warning(f"Could not remove temporary attachment file '{filepath}': {e}")

        return clean_markdown("\n".join(markdown_parts))
