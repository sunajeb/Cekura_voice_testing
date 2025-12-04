"""
Cekura API Client
Handles all interactions with the Cekura API
"""
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import requests

logger = logging.getLogger(__name__)

# Request timeout in seconds (30 seconds for API calls)
REQUEST_TIMEOUT = 30


class CekuraClient:
    """Client for interacting with Cekura Test Framework API"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.cekura.ai/test_framework/v1"
        self.headers = {"X-CEKURA-API-KEY": self.api_key}

    def get_latest_result(self, agent_id: int, expected_run_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Fetch the latest result for a given agent, optionally filtering by run name.

        Args:
            agent_id: The agent ID to fetch results for
            expected_run_name: Optional run name to match (e.g., "API_Dec 4")

        Returns:
            Latest result dict or None if no results found
        """
        try:
            response = requests.get(
                f"{self.base_url}/results/",
                headers=self.headers,
                params={"agent": agent_id},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if not results:
                logger.warning(f"No results found for agent {agent_id}")
                return None

            # Filter results to only include this agent (API filter doesn't always work)
            agent_results = [r for r in results if r.get("agent") == agent_id]

            if not agent_results:
                logger.warning(f"No results found for agent {agent_id} after filtering")
                return None

            # If expected_run_name is provided, try to find matching result first
            if expected_run_name:
                matching_results = [
                    r for r in agent_results
                    if r.get("name") == expected_run_name
                ]
                if matching_results:
                    latest = matching_results[0]
                    logger.info(f"Found result matching run name '{expected_run_name}' for agent {agent_id}")
                else:
                    logger.warning(f"No result matching run name '{expected_run_name}' for agent {agent_id}, using latest")
                    latest = agent_results[0]
            else:
                # Get the most recent result
                latest = agent_results[0]

            result_id = latest["id"]

            # Fetch full details including overall_evaluation
            return self.get_result_by_id(result_id)

        except Exception as e:
            logger.error(f"Error fetching latest result for agent {agent_id}: {e}")
            return None

    def get_result_by_id(self, result_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a specific result by ID.

        Args:
            result_id: The result ID to fetch

        Returns:
            Result dict or None if not found
        """
        try:
            response = requests.get(
                f"{self.base_url}/results/{result_id}/",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Error fetching result {result_id}: {e}")
            return None

    def discover_scenarios(self, agent_id: int, max_results: int = 20) -> List[int]:
        """
        Auto-discover ALL scenarios configured for an agent by checking result history.

        Args:
            agent_id: The agent ID
            max_results: Maximum number of historical results to check (default 20)

        Returns:
            List of unique scenario IDs
        """
        try:
            # Fetch recent results for the agent
            response = requests.get(
                f"{self.base_url}/results/",
                headers=self.headers,
                params={"agent": agent_id},
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            results = data.get("results", [])

            if not results:
                logger.warning(f"No results found for agent {agent_id}")
                return []

            # Filter results to only include this agent (API filter doesn't always work)
            agent_results = [r for r in results if r.get("agent") == agent_id][:max_results]

            if not agent_results:
                logger.warning(f"No results found for agent {agent_id} after filtering")
                return []

            # Collect all unique scenario IDs from result history
            all_scenarios = set()
            for result in agent_results:
                scenarios = result.get("scenarios", [])
                for s in scenarios:
                    all_scenarios.add(s["id"])

            scenario_list = sorted(list(all_scenarios))
            logger.info(f"Discovered {len(scenario_list)} unique scenarios for agent {agent_id}")
            return scenario_list

        except Exception as e:
            logger.error(f"Error discovering scenarios for agent {agent_id}: {e}")
            return []

    def run_scenarios(
        self,
        agent_id: int,
        scenarios: List[int],
        run_name: Optional[str] = None
    ) -> Optional[int]:
        """
        Trigger a test run for specified scenarios.

        Args:
            agent_id: The agent ID to test
            scenarios: List of scenario IDs to run
            run_name: Optional name for the test run

        Returns:
            Result ID if successful, None otherwise
        """
        if not scenarios:
            logger.error(f"No scenarios provided for agent {agent_id}")
            return None

        payload = {
            "agent_id": agent_id,
            "scenarios": scenarios
        }

        if run_name:
            payload["name"] = run_name

        try:
            response = requests.post(
                f"{self.base_url}/scenarios/run_scenarios/",
                headers={**self.headers, "Content-Type": "application/json"},
                json=payload,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            data = response.json()
            result_id = data.get("id")
            logger.info(f"Test run triggered for agent {agent_id}, result ID: {result_id}")
            return result_id

        except Exception as e:
            logger.error(f"Error triggering test run for agent {agent_id}: {e}")
            return None

    def wait_for_completion(
        self,
        result_id: int,
        timeout: int = 600,
        poll_interval: int = 10
    ) -> Optional[Dict[str, Any]]:
        """
        Poll a result until it completes or times out.

        Args:
            result_id: The result ID to poll
            timeout: Maximum time to wait in seconds
            poll_interval: Time between polls in seconds

        Returns:
            Completed result dict or None if timeout/error
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                result = self.get_result_by_id(result_id)

                if not result:
                    logger.error(f"Failed to fetch result {result_id}")
                    return None

                status = result.get("status")
                completed = result.get("completed_runs_count", 0)
                total = result.get("total_runs_count", 0)

                logger.info(f"Result {result_id}: {status} - {completed}/{total} runs completed")

                if status == "completed":
                    logger.info(f"Result {result_id} completed successfully")
                    return result
                elif status == "failed":
                    logger.error(f"Result {result_id} failed")
                    return None

                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error polling result {result_id}: {e}")
                return None

        logger.warning(f"Timeout waiting for result {result_id}")
        return None
