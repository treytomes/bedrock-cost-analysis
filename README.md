# Bedrock Live Cost Monitor

A Python utility to monitor AWS Bedrock inference costs in real-time by tailing CloudWatch logs.

## Features
- **Real-time Monitoring:** Tails CloudWatch Log Groups for model invocation events.
- **Dynamic Pricing:** Fetches the latest Bedrock pricing from the AWS Price List API.
- **Cost Attribution:** Breaks down costs by IAM user/role (ARN).
- **Persistent Storage:** Saves all events to a local SQLite database for historical reporting.
- **Interactive Dashboard:** Live terminal UI using `rich`.

## Prerequisites

**AWS Credentials:** Ensure you have an active SSO session for the profile configured in `config.yaml` (default: `branch-dev`).

## Setup

1. **Create virtual environment and install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure `config.yaml`:**
   Set your AWS profile, region, and desired CloudWatch log group name. The defaults match the standard Bedrock logging setup.

3. **Enable Bedrock invocation logging:**
   Run the included setup script to create the CloudWatch log group, IAM role, and Bedrock logging configuration automatically:
   ```bash
   python setup_logging.py
   ```
   This is a one-time step per AWS account. The script is idempotent — safe to re-run if anything changes.

   You can override config.yaml defaults via flags:
   ```bash
   python setup_logging.py --profile my-profile --region us-west-2 --log-group /my/log/group
   ```

4. **Run the monitor:**
   ```bash
   python main.py
   ```

## setup_logging.py

Automates the AWS setup required before the monitor can receive data. Bedrock model invocation logging is opt-in and requires infrastructure that this script creates:

| Resource | Name | Notes |
|----------|------|-------|
| CloudWatch log group | `/aws/bedrock/model-invocation-logs` (configurable) | Created if absent |
| IAM role | `BedrockInvocationLoggingRole` | Trust policy scoped to your account and region |
| IAM inline policy | `BedrockInvocationLoggingPolicy` | Grants `logs:CreateLogStream` and `logs:PutLogEvents` on the log group |
| Bedrock logging config | — | Enables text delivery to CloudWatch; S3 delivery is not configured |

The script reads defaults from `config.yaml` and verifies the configuration was applied before exiting. IAM roles require ~10 seconds to propagate before Bedrock will accept them; the script waits automatically.

**Required IAM permissions for the user running the script:**
- `logs:CreateLogGroup`
- `iam:CreateRole`, `iam:GetRole`, `iam:UpdateAssumeRolePolicy`, `iam:PutRolePolicy`
- `bedrock:PutModelInvocationLoggingConfiguration`, `bedrock:GetModelInvocationLoggingConfiguration`

## Project Structure
- `main.py` — Entry point and live dashboard logic
- `setup_logging.py` — One-time AWS setup for Bedrock invocation logging
- `pricing_fetcher.py` — Downloads and parses AWS Bedrock pricing data
- `log_monitor.py` — Tails and parses CloudWatch log events
- `cost_engine.py` — Calculates USD cost based on token counts
- `database.py` — SQLite persistence layer
- `config.yaml` — Central configuration file
