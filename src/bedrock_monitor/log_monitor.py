import boto3
import json
import time
import logging
import os
from datetime import datetime, timedelta
from botocore.exceptions import ClientError, EndpointConnectionError, ConnectTimeoutError

class LogMonitor:
    def __init__(self, config):
        self.config = config
        self.region = config['aws']['region']
        self.profile = config['aws']['profile']
        self.log_group = config['aws']['log_group_name']
        self.state_file = os.getenv("STATE_FILE", "monitor_state.json")
        
        # Initialize boto3 session
        self.session = boto3.Session(profile_name=self.profile, region_name=self.region)
        self.client = self.session.client('logs')
        
        self.next_token = None
        self._load_state()

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                self.next_token = state.get('next_token')
                logging.info(f"Resuming from saved token (saved at {state.get('saved_at')})")
            except Exception as e:
                logging.warning(f"Could not load state file: {e}")

    def _save_state(self):
        try:
            tmp_path = self.state_file + ".tmp"
            with open(tmp_path, 'w') as f:
                json.dump({
                    "next_token": self.next_token,
                    "saved_at": datetime.now().isoformat()
                }, f)
            os.replace(tmp_path, self.state_file)
        except Exception as e:
            logging.error(f"Failed to save state file: {e}")

    def get_new_logs(self, start_time=None):
        """
        Polls for new log events since the last run or a specific start time.
        """
        params = {
            'logGroupName': self.log_group,
            'interleaved': True
        }

        if self.next_token:
            params['nextToken'] = self.next_token
        elif start_time:
            params['startTime'] = int(start_time.timestamp() * 1000)
        else:
            five_mins_ago = datetime.now() - timedelta(minutes=5)
            params['startTime'] = int(five_mins_ago.timestamp() * 1000)

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.filter_log_events(**params)
                self.next_token = response.get('nextToken')
                if self.next_token:
                    self._save_state()
                events = response.get('events', [])
                return [self._parse_event(e) for e in events]
            except (ClientError, EndpointConnectionError, ConnectTimeoutError) as e:
                logging.warning(f"AWS API attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    logging.error("All retries for CloudWatch logs failed.")
                    return []
            except Exception as e:
                logging.error(f"Unexpected error fetching logs: {e}")
                return []

    def _parse_event(self, event):
        """
        Parses a single CloudWatch log event into a structured dict.
        """
        try:
            payload = json.loads(event['message'])
            
            data = {
                'requestId': payload.get('requestId'),
                'modelId': payload.get('modelId'),
                'timestamp': datetime.fromtimestamp(event['timestamp'] / 1000).isoformat(),
                'identityArn': payload.get('identity', {}).get('arn', 'unknown'),
                'inputTokenCount': payload.get('input', {}).get('inputTokenCount', 0),
                'outputTokenCount': payload.get('output', {}).get('outputTokenCount', 0),
                'cacheReadInputTokenCount': payload.get('input', {}).get('cacheReadInputTokenCount', 0),
                'cacheWriteInputTokenCount': payload.get('input', {}).get('cacheWriteInputTokenCount', 0),
            }
            return data
        except Exception as e:
            logging.debug(f"Skipping malformed log entry: {e}")
            return None
