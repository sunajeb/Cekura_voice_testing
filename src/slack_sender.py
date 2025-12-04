"""
Slack Sender
Formats and sends messages to Slack
"""
import os
import logging
from typing import Dict, List, Any
import requests

logger = logging.getLogger(__name__)

# Request timeout in seconds for Slack API
REQUEST_TIMEOUT = 10


class SlackSender:
    """Send formatted messages to Slack"""

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_table(
        self,
        markdown_table: str,
        summary: str = "",
        title: str = "Competitor Testing Results"
    ) -> bool:
        """
        Send a markdown table to Slack.

        Args:
            markdown_table: Markdown formatted table
            summary: Optional summary text
            title: Message title

        Returns:
            True if successful, False otherwise
        """
        # Convert markdown table to Slack mrkdwn format
        slack_message = self._format_for_slack(markdown_table, summary, title)

        try:
            response = requests.post(
                self.webhook_url,
                json=slack_message,
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            logger.info("Successfully sent message to Slack")
            return True

        except Exception as e:
            logger.error(f"Error sending message to Slack: {e}")
            return False

    def _format_for_slack(
        self,
        markdown_table: str,
        summary: str,
        title: str
    ) -> Dict[str, Any]:
        """
        Format markdown table for Slack blocks with clickable links.

        Args:
            markdown_table: Markdown formatted table
            summary: Summary text
            title: Message title

        Returns:
            Slack message payload
        """
        blocks = []

        # Title block
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": title
            }
        })

        # Summary block (if provided)
        if summary:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": summary
                }
            })

        # Parse table and create formatted sections with clickable links
        table_blocks = self._markdown_table_to_slack_blocks(markdown_table)
        blocks.extend(table_blocks)

        return {"blocks": blocks}

    def _markdown_table_to_slack_blocks(self, markdown_table: str) -> List[Dict[str, Any]]:
        """
        Convert markdown table to Slack blocks with clickable links.

        Args:
            markdown_table: Markdown formatted table

        Returns:
            List of Slack block dicts
        """
        blocks = []
        lines = markdown_table.strip().split("\n")

        if len(lines) < 3:
            return blocks

        # Parse header
        header_line = lines[0]
        headers = [h.strip() for h in header_line.split("|") if h.strip()]

        # Add header as section
        header_text = " | ".join(f"*{h}*" for h in headers)
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": header_text
            }
        })

        # Add divider
        blocks.append({"type": "divider"})

        # Parse data rows
        for i, line in enumerate(lines):
            if i <= 1:  # Skip header and separator
                continue

            cells = [c.strip() for c in line.split("|") if c.strip()]

            if len(cells) != len(headers):
                continue

            # Build row text with proper Slack markdown for links
            row_parts = []
            for j, (header, cell) in enumerate(zip(headers, cells)):
                # Convert markdown link [Link](url) to Slack link <url|Link>
                if cell.startswith("[") and "](" in cell:
                    # Extract link text and URL
                    link_text = cell[cell.find("[")+1:cell.find("]")]
                    url = cell[cell.find("(")+1:cell.find(")")]
                    slack_link = f"<{url}|{link_text}>"
                    row_parts.append(f"*{header}:* {slack_link}")
                else:
                    row_parts.append(f"*{header}:* {cell}")

            # Create section for this row
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "\n".join(row_parts)
                }
            })

            # Add divider between rows
            if i < len(lines) - 1:
                blocks.append({"type": "divider"})

        return blocks

    def send_error_notification(
        self,
        error_message: str,
        agent_name: str = None
    ) -> bool:
        """
        Send an error notification to Slack.

        Args:
            error_message: The error message
            agent_name: Optional agent name

        Returns:
            True if successful, False otherwise
        """
        title = "⚠️ Competitor Testing Error"
        if agent_name:
            title += f" - {agent_name}"

        message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": title
                    }
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"```{error_message}```"
                    }
                }
            ]
        }

        try:
            response = requests.post(
                self.webhook_url,
                json=message,
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"Error sending error notification to Slack: {e}")
            return False
