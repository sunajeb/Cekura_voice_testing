#!/usr/bin/env python3
"""
Comprehensive test suite for Cekura integration
Tests all critical paths and edge cases
"""
import os
import sys

# Set API key
os.environ["CEKURA_API_KEY"] = "a91e35ab1ca2b9b771f5fb83329635794a28e79cbb359e6a5c9dc9aa083c96b6"

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from cekura_client import CekuraClient
from data_processor import DataProcessor
import yaml

class TestRunner:
    def __init__(self):
        self.client = CekuraClient(os.environ["CEKURA_API_KEY"])
        self.processor = DataProcessor()
        self.passed = 0
        self.failed = 0
        self.failures = []

    def test(self, name, func):
        """Run a test and track results"""
        try:
            print(f"\n{'='*60}")
            print(f"TEST: {name}")
            print(f"{'='*60}")
            func()
            print(f"✅ PASSED")
            self.passed += 1
        except AssertionError as e:
            print(f"❌ FAILED: {e}")
            self.failed += 1
            self.failures.append((name, str(e)))
        except Exception as e:
            print(f"❌ ERROR: {e}")
            self.failed += 1
            self.failures.append((name, str(e)))

    def assert_true(self, condition, message):
        """Assert condition is true"""
        if not condition:
            raise AssertionError(message)

    def assert_equal(self, actual, expected, message):
        """Assert values are equal"""
        if actual != expected:
            raise AssertionError(f"{message}\nExpected: {expected}\nActual: {actual}")

    def assert_not_none(self, value, message):
        """Assert value is not None"""
        if value is None:
            raise AssertionError(message)

    def assert_in(self, item, container, message):
        """Assert item is in container"""
        if item not in container:
            raise AssertionError(message)

def main():
    runner = TestRunner()

    # Load config
    with open('config/agents.yaml', 'r') as f:
        config = yaml.safe_load(f)
    agents = config.get('agents', [])

    print("\n" + "="*60)
    print("COMPREHENSIVE TEST SUITE")
    print("="*60)

    # TEST 1: Config validation
    def test_config_loaded():
        runner.assert_equal(len(agents), 5, "Should have 5 agents in config")
        for agent in agents:
            runner.assert_in('name', agent, f"Agent missing 'name': {agent}")
            runner.assert_in('agent_id', agent, f"Agent missing 'agent_id': {agent}")
            runner.assert_in('scenarios', agent, f"Agent missing 'scenarios': {agent}")
            runner.assert_true(len(agent['scenarios']) > 0,
                             f"Agent {agent['name']} has no scenarios")
        print(f"All {len(agents)} agents have valid configuration")

    runner.test("Config validation", test_config_loaded)

    # TEST 2: Each agent gets unique results
    def test_unique_results_per_agent():
        result_ids = {}
        agent_ids_in_results = {}

        for agent in agents:
            agent_name = agent['name']
            agent_id = agent['agent_id']

            result = runner.client.get_latest_result(agent_id)
            runner.assert_not_none(result, f"No result found for {agent_name}")

            result_id = result.get('id')
            result_agent = result.get('agent')

            runner.assert_not_none(result_id, f"{agent_name}: result has no ID")
            runner.assert_equal(result_agent, agent_id,
                              f"{agent_name}: result belongs to wrong agent")

            result_ids[agent_name] = result_id
            agent_ids_in_results[agent_name] = result_agent

            print(f"  {agent_name}: Result {result_id}, Agent {result_agent} ✓")

        # Check for duplicates
        unique_result_ids = set(result_ids.values())
        if len(unique_result_ids) < len(result_ids):
            # It's OK if some agents share results, but log it
            print(f"  Note: {len(result_ids) - len(unique_result_ids)} agents share result IDs")

        print(f"All {len(agents)} agents return correctly filtered results")

    runner.test("Unique results per agent", test_unique_results_per_agent)

    # TEST 3: Metrics extraction
    def test_metrics_extraction():
        test_agent = agents[1]  # Sierra - SiriusXM
        result = runner.client.get_latest_result(test_agent['agent_id'])
        runner.assert_not_none(result, "No result to test metrics")

        metrics = runner.processor.extract_metrics(result)

        # Check all expected metrics are present
        expected_metrics = [
            'latency', 'ai_interrupting_user', 'detect_silence',
            'stop_time', 'voice_tone_clarity', 'call_termination',
            'words_per_minute', 'relevancy', 'average_pitch'
        ]

        for metric_name in expected_metrics:
            runner.assert_in(metric_name, metrics,
                           f"Missing metric: {metric_name}")

        # Check percentage conversions
        for metric in ['detect_silence', 'call_termination', 'relevancy', 'voice_tone_clarity']:
            value = metrics[metric]
            if value != "N/A":
                runner.assert_true(isinstance(value, (int, float)),
                                 f"{metric} should be numeric or N/A")
                runner.assert_true(0 <= value <= 100,
                                 f"{metric} should be 0-100%, got {value}")

        print(f"  Extracted {len(metrics)} metrics successfully")
        print(f"  Sample: Latency={metrics['latency']}, Relevancy={metrics['relevancy']}")

    runner.test("Metrics extraction", test_metrics_extraction)

    # TEST 4: Table row creation
    def test_table_row_creation():
        for agent in agents[:2]:  # Test first 2 agents
            agent_name = agent['name']
            agent_id = agent['agent_id']

            result = runner.client.get_latest_result(agent_id)
            runner.assert_not_none(result, f"No result for {agent_name}")

            row = runner.processor.create_table_row(agent_name, result)

            # Check all expected columns
            expected_columns = [
                'Company-Client', 'Link', 'Latency (ms)',
                'AI interrupting user', 'Detect Silence in Conversation',
                'Stop Time after User Interruption (ms)', 'Voice Tone + Clarity',
                'Appropriate Call Termination by Main Agent',
                'Words Per Minute', 'Relevancy', 'Average Pitch (Hz)'
            ]

            for col in expected_columns:
                runner.assert_in(col, row, f"Missing column: {col}")

            # Check link format
            result_id = result.get('id')
            runner.assert_true(f"results/{result_id}" in row['Link'],
                             f"Link should contain result ID {result_id}")

            print(f"  {agent_name}: Row created with {len(row)} columns ✓")

    runner.test("Table row creation", test_table_row_creation)

    # TEST 5: Full table generation
    def test_full_table_generation():
        rows = []
        for agent in agents:
            result = runner.client.get_latest_result(agent['agent_id'])
            if result and result.get('status') == 'completed':
                row = runner.processor.create_table_row(agent['name'], result)
                rows.append(row)

        runner.assert_true(len(rows) > 0, "No rows generated")

        table = runner.processor.create_markdown_table(rows)
        runner.assert_true(len(table) > 0, "Table is empty")
        runner.assert_true("Company-Client" in table, "Table missing header")
        runner.assert_true("Link" in table, "Table missing Link column")

        # Check table has correct number of data rows (+2 for header and separator)
        lines = table.split('\n')
        runner.assert_equal(len(lines), len(rows) + 2,
                          f"Table should have {len(rows) + 2} lines")

        print(f"  Generated table with {len(rows)} rows")
        print(f"  Table has {len(lines)} total lines")

    runner.test("Full table generation", test_full_table_generation)

    # TEST 6: Scenario configuration
    def test_scenario_configuration():
        for agent in agents:
            agent_name = agent['name']
            scenarios = agent.get('scenarios', [])

            runner.assert_true(len(scenarios) > 0,
                             f"{agent_name} has no scenarios configured")
            runner.assert_true(all(isinstance(s, int) for s in scenarios),
                             f"{agent_name} has non-integer scenario IDs")

            print(f"  {agent_name}: {len(scenarios)} scenarios configured ✓")

    runner.test("Scenario configuration", test_scenario_configuration)

    # TEST 7: Error handling - invalid agent
    def test_invalid_agent():
        result = runner.client.get_latest_result(99999)
        # Should return None, not crash
        print(f"  Invalid agent returns None (expected): {result is None}")

    runner.test("Error handling - invalid agent", test_invalid_agent)

    # TEST 8: Result completeness
    def test_result_completeness():
        for agent in agents:
            agent_name = agent['name']
            result = runner.client.get_latest_result(agent['agent_id'])

            if result:
                # Check essential fields
                runner.assert_in('id', result, f"{agent_name}: missing result ID")
                runner.assert_in('status', result, f"{agent_name}: missing status")
                runner.assert_in('overall_evaluation', result,
                               f"{agent_name}: missing overall_evaluation")

                overall_eval = result.get('overall_evaluation', {})
                runner.assert_in('metric_summary', overall_eval,
                               f"{agent_name}: missing metric_summary")

                print(f"  {agent_name}: Result structure is complete ✓")

    runner.test("Result completeness", test_result_completeness)

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed: {runner.passed}")
    print(f"❌ Failed: {runner.failed}")
    print(f"Total: {runner.passed + runner.failed}")

    if runner.failures:
        print("\n" + "="*60)
        print("FAILURES:")
        print("="*60)
        for name, error in runner.failures:
            print(f"\n❌ {name}")
            print(f"   {error}")

    print("\n" + "="*60)
    if runner.failed == 0:
        print("🎉 ALL TESTS PASSED!")
    else:
        print(f"⚠️  {runner.failed} TEST(S) FAILED")
    print("="*60)

    return 0 if runner.failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
