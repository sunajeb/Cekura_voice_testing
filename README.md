# Cekura Competitor Testing Automation

Automated weekly testing of competitor voice agents using Cekura's testing framework, with results delivered to Slack.

## Overview

This project automates the process of:
1. **Triggering tests** for competitor voice agents (Friday 10:00 AM IST)
2. **Fetching results** and sending formatted reports to Slack (Friday 1:00 PM IST)

## Project Structure

```
cekura-competitor-testing/
├── .github/
│   └── workflows/
│       ├── trigger-tests.yml      # Cron job to trigger tests
│       └── fetch-results.yml      # Cron job to fetch and send results
├── config/
│   └── agents.yaml               # Agent configuration (easy to update)
├── src/
│   ├── cekura_client.py         # Cekura API client
│   ├── data_processor.py        # Metrics extraction and formatting
│   ├── slack_sender.py          # Slack integration
│   └── main.py                  # Main orchestrator
├── requirements.txt
└── README.md
```

## Setup

### 1. GitHub Secrets

Add the following secrets to your GitHub repository (Settings → Secrets and variables → Actions):

- `CEKURA_API_KEY`: Your Cekura API key
- `SLACK_WEBHOOK_URL`: Your Slack webhook URL

### 2. Agent Configuration

Edit `config/agents.yaml` to add or modify agents:

```yaml
agents:
  - name: "Sierra - SiriusXM"
    agent_id: 10141
    scenarios:
      - 72708
      - 72709
      - 72710
      # ... add scenario IDs

  - name: "Poly - SimplyHealth"
    agent_id: 10143
    scenarios:
      - 72721
      - 72722
      # ... add scenario IDs
```

**Note**: Scenarios are stored in the config file for reliability and speed. To update scenarios for an agent, modify the list in the config.

## Usage

### Automated (GitHub Actions)

The system runs automatically via GitHub Actions:
- **Friday 10:00 AM IST**: Triggers tests for all configured agents
- **Friday 1:00 PM IST**: Fetches results and sends report to Slack

You can also manually trigger workflows from the GitHub Actions tab.

### Manual (Local Testing)

#### Install Dependencies

```bash
pip install -r requirements.txt
```

#### Set Environment Variables

```bash
export CEKURA_API_KEY="your-api-key"
export SLACK_WEBHOOK_URL="your-webhook-url"
```

#### Trigger Tests

```bash
cd src
python main.py trigger
```

#### Fetch Results

```bash
cd src
python main.py fetch
```

## Output Format

Results are sent to Slack in a formatted table with the following metrics:

- **Latency (ms)**: Average response time
- **AI interrupting user**: Number of AI interruptions
- **Detect Silence in Conversation**: Percentage of silence detection
- **Stop Time after User Interruption (ms)**: Response time after interruption
- **Voice Tone + Clarity**: Voice quality score
- **Appropriate Call Termination by Main Agent**: Call termination success rate
- **Words Per Minute**: Speaking rate
- **Relevancy**: Response relevancy score
- **Average Pitch (Hz)**: Voice pitch

Each row includes a link to the detailed Cekura report.

## Error Handling

- **Test trigger failures**: Automatically retries up to 3 times
- **Missing results**: Shows "N/A" in the table
- **Partial failures**: Sends results for successful agents, logs failures

## Adding New Agents

1. Create and configure the agent in Cekura
2. Run at least one test manually in Cekura with all desired scenarios
3. Get the scenario IDs from the test result
4. Add the agent to `config/agents.yaml`:
   ```yaml
   - name: "Company - Client"
     agent_id: <agent_id>
     scenarios:
       - <scenario_id_1>
       - <scenario_id_2>
       # ... add all scenario IDs
   ```
5. Commit and push changes

## Test Naming Convention

All test runs are named with the format: `API_MMM D` (e.g., `API_Dec 4`)

This makes it easy to track weekly test runs in Cekura.

## Maintenance

- **Update agent list**: Edit `config/agents.yaml`
- **Change schedule**: Edit cron expressions in `.github/workflows/*.yml`
- **Modify metrics**: Update `METRIC_CODES` in `src/data_processor.py`

## Troubleshooting

### Tests not triggering
- Check GitHub Actions logs
- Verify `CEKURA_API_KEY` is set correctly
- Ensure agents have previous test runs (for scenario discovery)

### Results not appearing in Slack
- Verify `SLACK_WEBHOOK_URL` is correct
- Check that tests have completed (3-hour gap should be sufficient)
- Review logs in GitHub Actions

### Missing metrics in output
- Some metrics may return `N/A` if not available for a specific test
- Verify the agent is properly configured in Cekura

## License

Internal use only.
