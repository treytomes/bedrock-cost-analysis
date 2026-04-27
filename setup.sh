#!/usr/bin/env bash
set -e

VENV_DIR=".venv"

echo "=== Bedrock Cost Monitor Setup ==="
echo

# 1. Python version check
python_bin=$(command -v python3 || command -v python || true)
if [[ -z "$python_bin" ]]; then
    echo "Error: Python 3.10+ is required but was not found on PATH."
    exit 1
fi

python_version=$("$python_bin" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
python_major=$(echo "$python_version" | cut -d. -f1)
python_minor=$(echo "$python_version" | cut -d. -f2)
if (( python_major < 3 || (python_major == 3 && python_minor < 10) )); then
    echo "Error: Python 3.10+ is required (found $python_version)."
    exit 1
fi
echo "Python $python_version ... OK"

# 2. Create virtualenv if absent
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment..."
    "$python_bin" -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

# 3. Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# 4. Create .env if absent
if [[ ! -f ".env" ]]; then
    cp .env.example .env
    echo
    echo "Created .env from .env.example."
    echo "Please enter your AWS profile name (the profile configured in ~/.aws/config):"
    read -r aws_profile
    if [[ -n "$aws_profile" ]]; then
        sed -i "s/^AWS_PROFILE=.*/AWS_PROFILE=${aws_profile}/" .env
        echo "AWS_PROFILE set to '${aws_profile}'."
    else
        echo "Warning: AWS_PROFILE not set. Edit .env before running the monitor."
    fi
else
    echo ".env already exists, skipping."
fi

# 5. Verify AWS credentials
echo
echo "Verifying AWS credentials..."
source .env
if aws sts get-caller-identity --profile "$AWS_PROFILE" > /dev/null 2>&1; then
    echo "AWS credentials for profile '${AWS_PROFILE}' ... OK"
else
    echo "Warning: Could not verify AWS credentials for profile '${AWS_PROFILE}'."
    echo "  Make sure the profile exists in ~/.aws/config and your session is active."
    echo "  For SSO profiles: aws sso login --profile ${AWS_PROFILE}"
fi

# 6. Run bedrock logging setup
echo
echo "Configuring Bedrock invocation logging in AWS..."
python -m bedrock_monitor.setup_logging

echo
echo "=== Setup complete ==="
echo "Start the monitor with:  ./start.sh"
