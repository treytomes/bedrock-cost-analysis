import importlib.resources
import os
import shutil
import sys


def main():
    files = {
        "config.yaml": "config.yaml",
        ".env.example": ".env.example",
    }

    any_skipped = False
    for src_name, dest_name in files.items():
        dest = os.path.join(os.getcwd(), dest_name)
        if os.path.exists(dest):
            print(f"  skipped  {dest_name} (already exists)")
            any_skipped = True
            continue
        ref = importlib.resources.files("bedrock_monitor.data").joinpath(src_name)
        with importlib.resources.as_file(ref) as src_path:
            shutil.copy(src_path, dest)
        print(f"  created  {dest_name}")

    print()
    if any_skipped:
        print("Some files already exist and were not overwritten.")
    print("Next steps:")
    print("  1. Copy .env.example to .env and set AWS_PROFILE")
    print("  2. Run: bedrock-monitor-setup   (one-time AWS setup)")
    print("  3. Run: bedrock-monitor")
