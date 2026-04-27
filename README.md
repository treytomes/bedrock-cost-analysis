# Bedrock Live Cost Monitor

A Python utility to monitor AWS Bedrock inference costs in real-time by tailing CloudWatch logs.

## Features
- **Real-time Monitoring:** Tails CloudWatch Log Groups for model invocation events.
- **Dynamic Pricing:** Fetches the latest Bedrock pricing from the AWS Price List API.
- **Cost Attribution:** Breaks down costs by IAM user/role (ARN).
- **Persistent Storage:** Saves all events to a local SQLite database for historical reporting.
- **Interactive Dashboard:** Live terminal UI using `rich`.

## Requirements

- Python 3.10+
- An active AWS credentials profile with access to Bedrock and CloudWatch Logs

## Setup

1. **Create virtual environment and install dependencies:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure your environment:**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set `AWS_PROFILE` to your AWS credentials profile name. All other defaults are suitable for most setups.

3. **Enable Bedrock invocation logging (one-time per account):**
   ```bash
   python setup_logging.py
   ```
   This creates the CloudWatch log group, IAM role, and Bedrock logging configuration automatically. The script is idempotent — safe to re-run.

   You can override `.env` defaults via flags:
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
- `config.yaml` — Central configuration (non-sensitive defaults)
- `.env` — Environment-specific values (not committed; see `.env.example`)

## Troubleshooting

**No invocations appearing in the dashboard**
- Confirm Bedrock invocation logging is enabled: run `python setup_logging.py` and check for errors.
- Verify the log group name in `.env` matches what Bedrock is writing to (AWS Console → Bedrock → Settings → Logging).
- CloudWatch events can lag by up to 1–2 minutes after an invocation.

**"No pricing data for model" warnings**
- The AWS Price List API lags behind new model releases. Static fallback prices are used automatically for known models.
- Delete `prices_cache.json` to force a fresh fetch from the API.

**AWS credentials expired**
- Re-authenticate: `aws sso login --profile <your-profile>`
- For SSO profiles, sessions expire after the duration set in IAM Identity Center (typically 1–8 hours).

**Database locked error**
- Only one instance of the monitor should run at a time against the same `DATABASE_FILE`.

**Monitor not shutting down cleanly**
- The monitor handles `SIGTERM` and `SIGINT` (Ctrl+C) for graceful shutdown.
