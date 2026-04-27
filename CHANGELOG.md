# Changelog

## [1.0.0] - 2026-04-27

Initial release.

### Features
- Real-time CloudWatch log tail for Bedrock model invocation events
- Live terminal dashboard (model usage, cost by identity, recent invocations) via `rich`
- Automatic pricing fetch from AWS Price List API with local cache and static fallback for new models
- Cost attribution by IAM ARN
- SQLite persistence for historical reporting
- One-time AWS setup script (`bedrock-monitor-setup`) for CloudWatch log group, IAM role, and Bedrock logging config

### Notes
- Requires Python 3.10+
- AWS profile configured via `.env` (see `.env.example`)
