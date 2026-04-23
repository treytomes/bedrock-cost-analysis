# Project Requirements: Bedrock Live Cost Monitor

## Functional Requirements
- **Dynamic Pricing Sync:** Must fetch `AmazonBedrock` pricing from `https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonBedrock/current/index.json`.
- **Log Tailing:** Must support continuous monitoring of a specified CloudWatch Log Group.
- **Cost Calculation:**
    - Handle standard Input/Output token pricing.
    - Handle Prompt Caching (Read/Write) if present in logs.
- **Reporting:**
    - Show real-time spend in the terminal.
    - Breakdown costs by `identity.arn`.
- **Data Persistence:** Save all invocation metadata to SQLite.

## Technical Requirements
- **Language:** Python 3.x
- **Libraries:**
    - `boto3`: AWS SDK for CloudWatch and Pricing.
    - `requests`: For fetching the public pricing JSON.
    - `rich`: For terminal formatting.
    - `pyyaml`: For configuration management.
- **Authentication:** Must use the `branch-dev` AWS profile (managed via environment variables or local AWS config).

## Data Schema (SQLite)
- **Table: `invocations`**
    - `request_id` (PK)
    - `timestamp`
    - `model_id`
    - `identity_arn`
    - `input_tokens`
    - `output_tokens`
    - `cache_read_tokens`
    - `cache_write_tokens`
    - `cost_usd`
