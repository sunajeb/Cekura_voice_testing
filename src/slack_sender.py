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
        Convert markdown table to proper table format with visual charts.

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
        agent_links = []
        for i, line in enumerate(lines):
            if i <= 1:  # Skip header and separator
                continue
            cells = [c.strip() for c in line.split("|") if c.strip()]
            if len(cells) == len(headers):
                agents_data.append(cells)

                # Extract link
                link_cell = cells[1]
                if link_cell.startswith("[") and "](" in link_cell:
                    url = link_cell[link_cell.find("(")+1:link_cell.find(")")]
                    agent_links.append(url)
                else:
                    agent_links.append(None)

        if not agents_data:
            return blocks

        # Create ASCII table
        table_text = self._create_ascii_table(headers, agents_data, agent_links)

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"```\n{table_text}\n```"
            }
        })

        # Add visual charts for key metrics
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*📊 Visual Comparison (Key Metrics)*"
            }
        })

        # Select key metrics to visualize
        key_metrics = ["Latency (ms)", "AI interrupting user", "Voice Tone + Clarity", "Relevancy"]

        for metric_name in key_metrics:
            if metric_name in headers:
                metric_idx = headers.index(metric_name)
                chart_block = self._create_bar_chart(metric_name, agents_data, metric_idx)
                if chart_block:
                    blocks.append(chart_block)

        return blocks

    def _create_ascii_table(self, headers: List[str], agents_data: List[List[str]], agent_links: List[str]) -> str:
        """
        Create a properly formatted ASCII table.

        Args:
            headers: Column headers
            agents_data: All agent data rows
            agent_links: Links for each agent

        Returns:
            ASCII table string
        """
        # Get agent names (short version)
        agent_names = [row[0].replace(" - ", "\n") for row in agents_data]

        # Calculate column widths
        col_width = 12  # Fixed width for readability
        metric_width = 25

        # Build header row
        header = f"{'Metric':<{metric_width}}"
        for name in agent_names:
            # Use first part of name only
            short_name = name.split("\n")[0]
            header += f" │ {short_name:^{col_width}}"

        # Build separator
        separator = "─" * metric_width + "─┼" + ("─" * (col_width + 2) + "┼") * (len(agent_names) - 1) + "─" * (col_width + 2)

        lines = [header, separator]

        # Build data rows (skip Company-Client and Link columns)
        for metric_idx in range(2, len(headers)):
            metric_name = headers[metric_idx]
            emoji = self._get_metric_emoji(metric_name)

            # Truncate long metric names
            display_name = f"{emoji} {metric_name}"
            if len(display_name) > metric_width:
                display_name = display_name[:metric_width-3] + "..."

            row = f"{display_name:<{metric_width}}"

            for agent_row in agents_data:
                value = agent_row[metric_idx]
                # Center align values
                row += f" │ {value:^{col_width}}"

            lines.append(row)

        return "\n".join(lines)

    def _create_bar_chart(self, metric_name: str, agents_data: List[List[str]], metric_idx: int) -> Dict[str, Any]:
        """
        Create a unicode bar chart for a metric.

        Args:
            metric_name: Name of the metric
            agents_data: All agent data
            metric_idx: Index of this metric in the data

        Returns:
            Slack block with bar chart
        """
        emoji = self._get_metric_emoji(metric_name)

        # Extract values
        values = []
        agent_names = []
        for row in agents_data:
            agent_name = row[0].split(" - ")[0]  # Company name only
            value_str = row[metric_idx]

            # Try to convert to float
            try:
                # Remove percentage sign if present
                if "%" in value_str:
                    value = float(value_str.replace("%", ""))
                else:
                    value = float(value_str)
                values.append(value)
                agent_names.append(agent_name)
            except:
                # Skip N/A values
                pass

        if not values:
            return None

        # Normalize values to bar length (max 20 chars)
        max_value = max(values)
        min_value = min(values)

        if max_value == min_value:
            # All values are the same
            bars = ["█" * 10 for _ in values]
        else:
            bars = []
            for v in values:
                # Scale to 1-20 range
                scaled = int(((v - min_value) / (max_value - min_value)) * 18) + 2
                bars.append("█" * scaled)

        # Build chart text
        chart_lines = [f"*{emoji} {metric_name}*"]
        for name, value, bar in zip(agent_names, values, bars):
            # Determine color based on metric (lower is better for latency, higher is better for percentages)
            if "Latency" in metric_name or "Stop Time" in metric_name or "interrupting" in metric_name:
                # Lower is better - use green for lowest
                color = "🟢" if value == min_value else "🟡" if value < (min_value + max_value) / 2 else "🔴"
            else:
                # Higher is better - use green for highest
                color = "🟢" if value == max_value else "🟡" if value > (min_value + max_value) / 2 else "🔴"

            chart_lines.append(f"{color} {name:15} {bar} `{value}`")

        return {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "\n".join(chart_lines)
            }
        }

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
