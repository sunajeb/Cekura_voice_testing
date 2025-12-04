"""
Slack Sender
Formats and sends messages to Slack
"""
import os
import logging
from typing import Dict, List, Any
import requests

logger = logging.getLogger(__name__)


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
                headers={"Content-Type": "application/json"}
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
        Format markdown table for Slack blocks.

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

        # Table block as preformatted text (monospace for alignment)
        # Convert markdown table to slack-friendly format
        table_text = self._markdown_to_slack_table(markdown_table)

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```\n{table_text}\n```"
            }
        })

        return {"blocks": blocks}

    def _markdown_to_slack_table(self, markdown_table: str) -> str:
        """
        Convert markdown table to a simpler format for Slack.

        Args:
            markdown_table: Markdown formatted table

        Returns:
            Simplified table string
        """
        lines = markdown_table.strip().split("\n")

        # Extract headers and remove separator row
        if len(lines) < 3:
            return markdown_table

        # Process each line to create aligned columns
        processed_lines = []
        for i, line in enumerate(lines):
            if i == 1:  # Skip separator row
                continue

            # Clean up the line
            clean_line = line.strip().strip("|").strip()
            # Replace multiple spaces with single space for better Slack rendering
            clean_line = " ".join(clean_line.split())
            processed_lines.append(clean_line)

        return "\n".join(processed_lines)

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
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return True

        except Exception as e:
            logger.error(f"Error sending error notification to Slack: {e}")
            return False
