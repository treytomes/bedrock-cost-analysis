import signal
import time
import yaml
import sys
import logging
import os
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.layout import Layout

from bedrock_monitor.pricing_fetcher import PricingFetcher
from bedrock_monitor.log_monitor import LogMonitor
from bedrock_monitor.database import Database
from bedrock_monitor.cost_engine import CostEngine

load_dotenv()

log_file = os.getenv("LOG_FILE", "bedrock_monitor.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        # StreamHandler omitted to avoid clashing with the Live dashboard
    ]
)

def load_config(path=None):
    if path is None:
        if os.path.exists('config.yaml'):
            path = 'config.yaml'
        else:
            print("No config.yaml found in current directory.")
            print("Run 'bedrock-monitor-init' to create one, then edit .env with your AWS_PROFILE.")
            sys.exit(1)
    try:
        with open(path, 'r') as f:
            raw = os.path.expandvars(f.read())
            config = yaml.safe_load(raw)

        required_keys = [
            ('aws', 'profile'), ('aws', 'region'), ('aws', 'log_group_name'),
            ('pricing', 'url'), ('pricing', 'cache_file'), ('pricing', 'refresh_hours'),
            ('database', 'file'),
            ('display', 'live_table_limit'), ('display', 'refresh_interval')
        ]

        missing = []
        for section, key in required_keys:
            if section not in config or key not in config[section]:
                missing.append(f"{section}.{key}")

        if missing:
            print(f"Error: Missing required config keys: {', '.join(missing)}")
            print("Check config.yaml and your .env file.")
            sys.exit(1)

        if config['display']['refresh_interval'] <= 0:
            print("Error: display.refresh_interval must be > 0")
            sys.exit(1)

        return config
    except FileNotFoundError:
        print(f"Error: config file not found at '{path}'")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading configuration: {e}")
        sys.exit(1)

def generate_dashboard(db, config):
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Summary Tables
    summary = db.get_daily_summary(today)
    user_summary = db.get_user_summary(today)
    recent = db.get_recent_invocations(limit=config['display']['live_table_limit'])

    # Table 1: Model Usage
    model_table = Table(title=f"Bedrock Usage Summary ({today})", expand=True)
    model_table.add_column("Model ID", style="cyan")
    model_table.add_column("Invocations", justify="right")
    model_table.add_column("Input Tokens", justify="right")
    model_table.add_column("Output Tokens", justify="right")
    model_table.add_column("Cost (USD)", style="green", justify="right")

    total_cost = 0
    for row in summary:
        cost_display = f"${row[4]:.4f}" if row[4] is not None else "[yellow]Pending[/yellow]"
        model_table.add_row(row[0], str(row[1]), str(row[2]), str(row[3]), cost_display)
        if row[4] is not None:
            total_cost += row[4]

    # Table 2: User Breakdown
    user_table = Table(title="Cost by Identity", expand=True)
    user_table.add_column("IAM ARN", style="magenta")
    user_table.add_column("Total Cost", style="green", justify="right")
    
    for row in user_summary:
        short_arn = row[0].split('/')[-1] if '/' in row[0] else row[0]
        cost_display = f"${row[1]:.4f}" if row[1] is not None else "[yellow]???[/yellow]"
        user_table.add_row(short_arn, cost_display)

    # Table 3: Recent Activity
    recent_table = Table(title="Recent Invocations", expand=True)
    recent_table.add_column("Time", style="dim")
    recent_table.add_column("Model", style="cyan")
    recent_table.add_column("Cost", style="green")

    for row in recent:
        time_str = row[0].split('T')[-1].split('.')[0]
        cost_display = f"${row[3]:.4f}" if row[3] is not None else "[yellow]???[/yellow]"
        recent_table.add_row(time_str, row[1], cost_display)

    # Layout
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main")
    )
    layout["main"].split_row(
        Layout(name="left"),
        Layout(name="right")
    )
    layout["left"].split_column(
        Layout(model_table),
        Layout(user_table)
    )
    layout["right"].update(recent_table)
    
    layout["header"].update(Panel(f"Total Daily Spend: [bold green]${total_cost:.2f}[/bold green] | [dim]Logs: {log_file}[/dim]", style="white"))
    
    return layout

def _handle_signal(sig, frame):
    logging.info(f"Received signal {sig}, shutting down.")
    sys.exit(0)


def main():
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    config = load_config()
    console = Console()

    logging.info("Bedrock Cost Monitor starting up...")

    # Initialize Modules
    try:
        pricing = PricingFetcher(config)
        pricing.fetch_prices()
        
        db = Database(config['database']['file'])
        monitor = LogMonitor(config)
        engine = CostEngine(pricing)
    except Exception as e:
        console.print(f"[bold red]Initialization Error:[/bold red] {e}")
        logging.error(f"Initialization Error: {e}")
        sys.exit(1)

    console.print(f"[bold blue]Bedrock Cost Monitor Started.[/bold blue] (Logs written to {log_file})")
    console.print("Press Ctrl+C to stop.")

    with Live(generate_dashboard(db, config), refresh_per_second=1/config['display']['refresh_interval']) as live:
        while True:
            # 1. Fetch new logs
            events = monitor.get_new_logs()

            # 2. Process events
            for event in events:
                if event is None:
                    continue

                # 3. Calculate cost
                event['costUsd'] = engine.calculate_cost(event)

                # 4. Save to DB
                db.insert_invocation(event)

            # 5. Update display
            live.update(generate_dashboard(db, config))

            time.sleep(config['display']['refresh_interval'])

if __name__ == "__main__":
    main()
