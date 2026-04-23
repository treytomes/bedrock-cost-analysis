# Project Plan: Bedrock Live Cost Monitor

## Objective
Develop a Python-based utility to monitor AWS Bedrock inference costs in real-time. The tool will tail CloudWatch logs and calculate costs dynamically using the latest pricing data fetched from the AWS Price List API.

## High-Level Strategy
1.  **Dynamic Pricing:** Instead of hard-coding values, the application will fetch the current `AmazonBedrock` pricing JSON from the AWS Price List endpoint and cache it locally.
2.  **Log Monitoring:** Use `boto3` to poll CloudWatch Log Groups for model invocation events.
3.  **Cost Attribution:** Aggregate costs by Model, IAM Identity, and Time Period.
4.  **Local Persistence:** Store all events and aggregated data in a SQLite database for durability and historical analysis.

## Architecture
- `pricing_fetcher.py`: Handles downloading and parsing the AWS Price List JSON.
- `log_monitor.py`: Logic for tailing and parsing CloudWatch logs.
- `cost_engine.py`: Core logic for calculating costs based on token counts and fetched rates.
- `database.py`: SQLite schema and data access layer.
- `dashboard.py`: CLI-based live reporting.

## Delivery Model
- The agent will write all scripts and documentation to `~/projects/bedrock-cost-analysis`.
- The agent will **not** execute the scripts.
- Verification will be done by the user in a subsequent session.
