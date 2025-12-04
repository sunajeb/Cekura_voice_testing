"""
Data Processor
Extracts and formats metrics from Cekura API results
"""
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Metric code mapping from Cekura API
METRIC_CODES = {
    "latency": "98797",
    "ai_interrupting_user": "98792",
    "detect_silence": "98796",
    "stop_time": "98804",
    "voice_tone_clarity": "98808",
    "call_termination": "98793",
    "words_per_minute": "98809",
    "relevancy": "98800",
    "average_pitch": "98794",
    "user_interrupting_ai": "100866"
}


class DataProcessor:
    """Process and format Cekura test results"""

    @staticmethod
    def extract_metrics(result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics from overall_evaluation.

        Args:
            result: Full result dict from Cekura API

        Returns:
            Dict of extracted metrics
        """
        overall_eval = result.get("overall_evaluation", {})
        metric_summary = overall_eval.get("metric_summary", {})

        metrics = {}

        # Extract each metric
        for metric_name, code in METRIC_CODES.items():
            if code in metric_summary:
                score = metric_summary[code].get("score")
                metrics[metric_name] = score if score is not None else "N/A"
            else:
                metrics[metric_name] = "N/A"

        # Convert binary metrics (0-5 scale) to percentages (0-100%)
        binary_metrics = ["detect_silence", "call_termination", "relevancy", "voice_tone_clarity"]
        for metric in binary_metrics:
            if metrics[metric] != "N/A" and isinstance(metrics[metric], (int, float)):
                metrics[metric] = (metrics[metric] / 5) * 100

        return metrics

    @staticmethod
    def format_value(value: Any, metric_type: str = "default") -> str:
        """
        Format a metric value for display.

        Args:
            value: The value to format
            metric_type: Type of metric (default, percentage, decimal)

        Returns:
            Formatted string
        """
        if value == "N/A" or value is None:
            return "N/A"

        if metric_type == "percentage":
            return f"{value:.1f}%"
        elif metric_type == "decimal":
            return f"{value:.2f}"
        elif isinstance(value, float):
            return f"{value:.2f}"
        else:
            return str(value)

    @staticmethod
    def create_table_row(
        agent_name: str,
        result: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Create a table row for a single agent result.

        Args:
            agent_name: Name of the agent (e.g., "Sierra - SiriusXM")
            result: Full result dict from Cekura API

        Returns:
            Dict with formatted row data
        """
        result_id = result.get("id")
        result_link = f"https://app.cekura.ai/results/{result_id}"

        metrics = DataProcessor.extract_metrics(result)

        return {
            "Company-Client": agent_name,
            "Link": f"[Link]({result_link})",
            "Latency (ms)": DataProcessor.format_value(metrics.get("latency")),
            "AI interrupting user": DataProcessor.format_value(metrics.get("ai_interrupting_user")),
            "User interrupting AI": DataProcessor.format_value(metrics.get("user_interrupting_ai")),
            "Detect Silence in Conversation": DataProcessor.format_value(
                metrics.get("detect_silence"), "percentage"
            ),
            "Stop Time after User Interruption (ms)": DataProcessor.format_value(
                metrics.get("stop_time")
            ),
            "Voice Tone + Clarity": DataProcessor.format_value(
                metrics.get("voice_tone_clarity"), "percentage"
            ),
            "Appropriate Call Termination by Main Agent": DataProcessor.format_value(
                metrics.get("call_termination"), "percentage"
            ),
            "Words Per Minute": DataProcessor.format_value(metrics.get("words_per_minute")),
            "Relevancy": DataProcessor.format_value(metrics.get("relevancy"), "percentage"),
            "Average Pitch (Hz)": DataProcessor.format_value(metrics.get("average_pitch"), "decimal")
        }

    @staticmethod
    def create_markdown_table(rows: List[Dict[str, str]]) -> str:
        """
        Create a markdown table from rows.

        Args:
            rows: List of row dicts

        Returns:
            Markdown formatted table string
        """
        if not rows:
            return "No data available"

        # Get headers from first row
        headers = list(rows[0].keys())

        # Create header row
        header_row = "| " + " | ".join(headers) + " |"
        separator_row = "| " + " | ".join(["---"] * len(headers)) + " |"

        # Create data rows
        data_rows = []
        for row in rows:
            values = [str(row.get(h, "N/A")) for h in headers]
            data_rows.append("| " + " | ".join(values) + " |")

        return "\n".join([header_row, separator_row] + data_rows)

    @staticmethod
    def generate_summary(results: List[Dict[str, Any]]) -> str:
        """
        Generate a summary of test results.

        Args:
            results: List of result tuples (agent_name, result_dict)

        Returns:
            Summary string
        """
        total = len(results)
        completed = sum(1 for r in results if r[1] is not None)
        failed = total - completed

        summary = f"**Test Results Summary**\n"
        summary += f"- Total Agents: {total}\n"
        summary += f"- Completed: {completed}\n"
        summary += f"- Failed: {failed}\n"

        return summary
