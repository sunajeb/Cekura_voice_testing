#!/usr/bin/env python3
"""
Main orchestrator for Cekura Competitor Testing
Handles triggering tests and fetching/sending results
"""
import os
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
import yaml

from cekura_client import CekuraClient
from data_processor import DataProcessor
from slack_sender import SlackSender

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_config() -> Dict[str, Any]:
    """Load agents configuration from YAML file"""
    config_path = Path(__file__).parent.parent / "config" / "agents.yaml"

    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
            logger.info(f"Loaded config with {len(config.get('agents', []))} agents")
            return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        sys.exit(1)


def get_run_name() -> str:
    """Generate run name in format: API_MMM D (e.g., API_Dec 4)"""
    now = datetime.now()
    return now.strftime("API_%b %-d")


def trigger_tests(cekura: CekuraClient, agents: List[Dict[str, Any]]) -> Dict[int, int]:
    """
    Trigger tests for all agents.

    Args:
        cekura: CekuraClient instance
        agents: List of agent configs

    Returns:
        Dict mapping agent_id to result_id
    """
    run_name = get_run_name()
    logger.info(f"Triggering tests with run name: {run_name}")

    result_map = {}
    failed_agents = []

    for agent in agents:
        agent_name = agent.get("name")
        agent_id = agent.get("agent_id")
        scenarios = agent.get("scenarios", [])

        logger.info(f"Processing agent: {agent_name} (ID: {agent_id})")

        if not scenarios:
            logger.warning(f"No scenarios configured for {agent_name}, skipping")
            failed_agents.append(agent_name)
            continue

        logger.info(f"Using {len(scenarios)} configured scenarios for {agent_name}")

        # Trigger test run with retry logic
        max_retries = 3
        result_id = None

        for attempt in range(max_retries):
            result_id = cekura.run_scenarios(agent_id, scenarios, run_name)

            if result_id:
                logger.info(f"Successfully triggered test for {agent_name} (result ID: {result_id})")
                result_map[agent_id] = result_id
                break
            else:
                logger.warning(f"Attempt {attempt + 1}/{max_retries} failed for {agent_name}")

        if not result_id:
            logger.error(f"Failed to trigger test for {agent_name} after {max_retries} attempts")
            failed_agents.append(agent_name)

    if failed_agents:
        logger.warning(f"Failed to trigger tests for: {', '.join(failed_agents)}")

    logger.info(f"Successfully triggered {len(result_map)}/{len(agents)} tests")
    return result_map


def fetch_results(
    cekura: CekuraClient,
    agents: List[Dict[str, Any]]
) -> List[Tuple[str, Dict[str, Any]]]:
    """
    Fetch latest results for all agents.

    Args:
        cekura: CekuraClient instance
        agents: List of agent configs

    Returns:
        List of tuples (agent_name, result_dict or None)
    """
    results = []

    for agent in agents:
        agent_name = agent.get("name")
        agent_id = agent.get("agent_id")

        logger.info(f"Fetching results for: {agent_name} (ID: {agent_id})")

        result = cekura.get_latest_result(agent_id)

        if result:
            # Check if result is completed
            status = result.get("status")
            if status == "completed":
                logger.info(f"Found completed result for {agent_name}")
                results.append((agent_name, result))
            else:
                logger.warning(f"Latest result for {agent_name} is not completed (status: {status})")
                results.append((agent_name, None))
        else:
            logger.warning(f"No results found for {agent_name}")
            results.append((agent_name, None))

    return results


def send_results(
    slack: SlackSender,
    results: List[Tuple[str, Dict[str, Any]]]
) -> bool:
    """
    Process and send results to Slack.

    Args:
        slack: SlackSender instance
        results: List of tuples (agent_name, result_dict or None)

    Returns:
        True if successful
    """
    processor = DataProcessor()

    # Create table rows for successful results
    rows = []
    for agent_name, result in results:
        if result:
            try:
                row = processor.create_table_row(agent_name, result)
                rows.append(row)
            except Exception as e:
                logger.error(f"Error creating row for {agent_name}: {e}")

    if not rows:
        logger.error("No valid results to send")
        return False

    # Generate markdown table
    table = processor.create_markdown_table(rows)

    # Generate summary
    total = len(results)
    completed = sum(1 for _, r in results if r is not None)
    failed = total - completed

    run_name = get_run_name()
    summary = f"*{run_name}*\n\n"
    summary += f"✅ Completed: {completed}/{total}\n"
    if failed > 0:
        summary += f"❌ Failed: {failed}\n"

    # Send to Slack
    success = slack.send_table(
        markdown_table=table,
        summary=summary,
        title="Weekly Competitor Testing Results"
    )

    return success


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Cekura Competitor Testing Automation")
    parser.add_argument(
        "action",
        choices=["trigger", "fetch"],
        help="Action to perform: trigger tests or fetch results"
    )
    args = parser.parse_args()

    # Load environment variables
    cekura_api_key = os.environ.get("CEKURA_API_KEY")
    slack_webhook_url = os.environ.get("SLACK_WEBHOOK_URL")

    if not cekura_api_key:
        logger.error("CEKURA_API_KEY environment variable not set")
        sys.exit(1)

    # Load config
    config = load_config()
    agents = config.get("agents", [])

    if not agents:
        logger.error("No agents configured")
        sys.exit(1)

    # Initialize client
    cekura = CekuraClient(cekura_api_key)

    if args.action == "trigger":
        # Trigger tests
        logger.info("Starting test trigger process...")
        result_map = trigger_tests(cekura, agents)

        if result_map:
            logger.info(f"Successfully triggered {len(result_map)} tests")
            # Save result IDs for reference
            for agent_id, result_id in result_map.items():
                print(f"Agent {agent_id}: Result ID {result_id}")
        else:
            logger.error("No tests were triggered successfully")
            sys.exit(1)

    elif args.action == "fetch":
        # Fetch results and send to Slack
        logger.info("Starting result fetch process...")

        if not slack_webhook_url:
            logger.error("SLACK_WEBHOOK_URL environment variable not set")
            sys.exit(1)

        results = fetch_results(cekura, agents)

        if not results:
            logger.error("No results to process")
            sys.exit(1)

        # Send to Slack
        slack = SlackSender(slack_webhook_url)
        success = send_results(slack, results)

        if success:
            logger.info("Successfully sent results to Slack")
        else:
            logger.error("Failed to send results to Slack")
            sys.exit(1)


if __name__ == "__main__":
    main()
