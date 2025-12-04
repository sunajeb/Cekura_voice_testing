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
        Convert markdown table to comparison view with agents as columns.

        Args:
            markdown_table: Markdown formatted table

        Returns:
            List of Slack block dicts
        """
        blocks = []
        lines = markdown_table.strip().split("\n")

        if len(lines) < 3:
            return blocks

        # Parse header and all data rows
        header_line = lines[0]
        headers = [h.strip() for h in header_line.split("|") if h.strip()]

        # Parse all agent rows
        agents_data = []
        for i, line in enumerate(lines):
            if i <= 1:  # Skip header and separator
                continue
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) == len(headers):
                agents_data.append(cells)

        if not agents_data:
            return blocks

        # Create agent header row with links
        agent_names = []
        for row in agents_data:
            agent_name = row[0]  # Company-Client
            link_cell = row[1]  # Link

            if link_cell.startswith("[") and "](" in link_cell:
                url = link_cell[link_cell.find("(")+1:link_cell.find(")")]
                agent_names.append(f"<{url}|*{agent_name}*>")
            else:
                agent_names.append(f"*{agent_name}*")

        # Add agent names header
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": " | ".join(agent_names)
            }
        })
        blocks.append({"type": "divider"})

        # Now display each metric as a row with values from all agents
        # Skip Company-Client (0) and Link (1)
        for metric_idx in range(2, len(headers)):
            metric_name = headers[metric_idx]
            emoji = self._get_metric_emoji(metric_name)

            # Collect values for this metric from all agents
            fields = []

            # Add metric name as first field (spans both columns)
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{emoji} *{metric_name}*"
                }
            })

            # Add values in a grid
            for row in agents_data:
                value = row[metric_idx]
                agent_name_short = row[0].split(" - ")[0]  # Get company name only

                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{agent_name_short}:* `{value}`"
                })

            # Add fields in groups (Slack supports max 10 fields)
            blocks.append({
                "type": "section",
                "fields": fields
            })

        return blocks

    def _get_metric_emoji(self, metric_name: str) -> str:
        """Get emoji for metric visualization."""
        emoji_map = {
            "Latency (ms)": "⚡",
            "AI interrupting user": "🔴",
            "User interrupting AI": "🔵",
            "Detect Silence in Conversation": "🔇",
            "Stop Time after User Interruption (ms)": "⏱️",
            "Voice Tone + Clarity": "🎙️",
            "Appropriate Call Termination by Main Agent": "✅",
            "Words Per Minute": "💬",
            "Relevancy": "🎯",
            "Average Pitch (Hz)": "🎵"
        }
        return emoji_map.get(metric_name, "📊")

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
