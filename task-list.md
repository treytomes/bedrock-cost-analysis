# Implementation Task List: Bedrock Live Cost Monitor

## Task 1: Environment Setup
- [x] Initialize git repository in `~/projects/bedrock-cost-analysis`.
- [x] Create `requirements.txt`.
- [x] Create `config.yaml` template.

## Task 2: Pricing Module
- [x] Implement `pricing_fetcher.py`.
- [x] Script should download the Bedrock index JSON.
- [x] Map `modelId` to `pricePerUnit` for Input/Output/Cache-Read/Cache-Write.
- [x] Store a local `prices.json` cache.

## Task 3: Database Module
- [x] Implement `database.py`.
- [x] Setup SQLite schema and connection handling.
- [x] Implement `insert_invocation` and `get_daily_summary` methods.

## Task 4: Log Monitor Module
- [x] Implement `log_monitor.py`.
- [x] Setup `boto3` CloudWatch client.
- [x] Implement token-based log tailing (using `getNextToken`).
- [x] Parse Bedrock log schema into internal `Invocation` objects.

## Task 5: Integration & CLI
- [x] Implement `main.py` to tie modules together.
- [x] Integrate `rich` for a clean CLI output.
- [x] Add graceful shutdown (Ctrl+C) handling.

## Task 6: Documentation
- [x] Move `project-plan.md`, `requirements.md`, and `task-list.md` into the project directory.
- [x] Create a `README.md` with setup and usage instructions.

---

## Task 7: Fix Silent $0 Cost on Unknown Models
- [x] Add a `logging` call at WARNING level when `rates` is empty.
- [x] Store a sentinel value (e.g. `cost_usd = None`) in the database for unpriceable invocations.
- [x] Startup warning/handling for unknown models.

---

## Task 8: Harden the Pricing Parser
- [x] Log a summary of SKU classification.
- [x] Log skipped SKUs at DEBUG level.
- [x] Add unit normalization logic with fallback warnings.

---

## Task 9: Add Configuration Validation at Startup
- [x] Validate all required keys in `config.yaml` before proceeding.
- [x] Raise clear error messages for missing keys.

---

## Task 10: Add Retry Logic for Network Calls
- [x] Wrap `requests.get()` with a retry loop and backoff.
- [x] Wrap `filter_log_events()` (boto3) with retry logic.

---

## Task 11: Add Database Indexes for Query Performance
- [x] Add indexes on `timestamp`, `identity_arn`, and `model_id`.

---

## Task 12: Persist Polling State Across Restarts
- [x] Persist `next_token` to `monitor_state.json`.
- [x] Load `next_token` on startup.

---

## Task 13: Replace print() with Structured Logging
- [x] Configure file logging in `main.py` (`bedrock_monitor.log`).
- [x] Replace `print()` with `logging` calls across all modules.
