# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated weekly testing system for competitor voice agents using Cekura's testing framework. The system triggers tests every Friday at 10:00 AM IST, fetches results at 1:00 PM IST, and sends formatted reports to Slack.

## Development Commands

### Local Testing
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export CEKURA_API_KEY="your-api-key"
export SLACK_WEBHOOK_URL="your-webhook-url"

# Trigger tests manually
cd src && python main.py trigger

# Fetch and send results
cd src && python main.py fetch
```

### Testing Specific Components
```bash
# Test with single agent (modify test_local.py)
python test_local.py

# Test full table generation
python test_full_table.py
```

## Architecture

### Core Components

1. **Main Orchestrator** (`src/main.py`)
   - Entry point for both trigger and fetch operations
   - Loads agent configuration from `config/agents.yaml`
   - Generates run names in format `API_MMM D` (e.g., `API_Dec 4`)
   - Implements retry logic (3 attempts) for test triggers
   - Coordinates between CekuraClient, DataProcessor, and SlackSender

2. **Cekura API Client** (`src/cekura_client.py`)
   - All interactions with Cekura API at `https://api.cekura.ai/test_framework/v1`
   - Key methods:
     - `run_scenarios()`: Triggers test runs with specified scenarios
     - `get_latest_result()`: Fetches most recent result for an agent
     - `get_result_by_id()`: Gets full result details including `overall_evaluation`
     - `discover_scenarios()`: Auto-discovers scenarios from result history (legacy, not used)
   - API authentication via `X-CEKURA-API-KEY` header

3. **Data Processor** (`src/data_processor.py`)
   - Extracts metrics from `overall_evaluation.metric_summary` using metric codes
   - Converts binary metrics (0-5 scale) to percentages: `detect_silence`, `call_termination`, `relevancy`, `voice_tone_clarity`
   - Formula: `(score / 5) * 100`
   - Handles missing values with "N/A"
   - Generates markdown tables for Slack

4. **Slack Sender** (`src/slack_sender.py`)
   - Sends formatted results via webhook
   - Creates summary with completion stats

### Data Flow

**Trigger Flow:**
1. Load agents from `config/agents.yaml`
2. Generate run name: `API_MMM D`
3. For each agent: POST to `/scenarios/run_scenarios/` with `agent_id` and `scenarios` list
4. Retry up to 3 times on failure
5. Log result IDs

**Fetch Flow:**
1. For each agent: GET `/results/?agent={agent_id}` to get latest result
2. GET `/results/{result_id}/` to get full details with `overall_evaluation`
3. Extract 9 metrics from `overall_evaluation.metric_summary` using metric codes
4. Convert binary metrics to percentages
5. Generate markdown table
6. POST to Slack webhook

### Configuration Structure

`config/agents.yaml` contains list of agents with:
- `name`: Display name (format: "Company - Client")
- `agent_id`: Cekura agent ID
- `scenarios`: List of scenario IDs to test

Scenarios are explicitly configured (not auto-discovered) for reliability and speed.

### Metric Codes

Defined in `src/data_processor.py:METRIC_CODES`:
- `98797`: Latency (ms)
- `98792`: AI interrupting user
- `98796`: Detect Silence in Conversation (converted to %)
- `98804`: Stop Time after User Interruption (ms)
- `98808`: Voice Tone + Clarity (converted to %)
- `98793`: Appropriate Call Termination (converted to %)
- `98809`: Words Per Minute
- `98800`: Relevancy (converted to %)
- `98794`: Average Pitch (Hz)

## GitHub Actions

### Workflows

1. **`trigger-tests.yml`**
   - Schedule: Friday 10:00 AM IST (04:30 UTC cron: `30 4 * * 5`)
   - Runs: `python main.py trigger`
   - Requires: `CEKURA_API_KEY` secret

2. **`fetch-results.yml`**
   - Schedule: Friday 1:00 PM IST (07:30 UTC cron: `30 7 * * 5`)
   - Runs: `python main.py fetch`
   - Requires: `CEKURA_API_KEY` and `SLACK_WEBHOOK_URL` secrets

Both support manual trigger via `workflow_dispatch`.

## Adding New Agents

1. Create agent in Cekura
2. Run at least one manual test with all desired scenarios
3. Get scenario IDs from test result
4. Add to `config/agents.yaml`:
   ```yaml
   - name: "Company - Client"
     agent_id: <agent_id>
     scenarios:
       - <scenario_id_1>
       - <scenario_id_2>
   ```

## Important Notes

- **Scenario Management**: Scenarios are explicitly configured in YAML, NOT auto-discovered. This prevents API filter bugs where scenarios from different agents could be mixed.
- **Result Timing**: 3-hour gap between trigger and fetch ensures tests complete.
- **Error Handling**: Partial failures are logged but don't block sending results for successful agents.
- **Naming Convention**: All test runs use `API_MMM D` format for easy tracking.
