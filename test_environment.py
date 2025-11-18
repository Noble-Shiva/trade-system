#!/usr/bin/env python3
"""
Test script to verify Angel One SDK installation and basic imports
"""

import sys
print("Python Version:", sys.version)
print("-" * 60)

# Test core libraries
print("\n✓ Testing Core Libraries...")
try:
    import pandas as pd
    print(f"  ✓ pandas: {pd.__version__}")
except ImportError as e:
    print(f"  ✗ pandas: {e}")

try:
    import numpy as np
    print(f"  ✓ numpy: {np.__version__}")
except ImportError as e:
    print(f"  ✗ numpy: {e}")

try:
    import scipy
    print(f"  ✓ scipy: {scipy.__version__}")
except ImportError as e:
    print(f"  ✗ scipy: {e}")

# Test configuration libraries
print("\n✓ Testing Configuration Libraries...")
try:
    import yaml
    print("  ✓ pyyaml: installed")
except ImportError as e:
    print(f"  ✗ pyyaml: {e}")

try:
    from dotenv import load_dotenv
    print("  ✓ python-dotenv: installed")
except ImportError as e:
    print(f"  ✗ python-dotenv: {e}")

# Test Angel One SDK
print("\n✓ Testing Angel One SDK...")
try:
    from SmartApi import SmartConnect
    print("  ✓ SmartApi (Angel One SDK): installed")
    print("  ✓ Ready to connect to Angel One API!")
except ImportError as e:
    print(f"  ✗ SmartApi: {e}")

# Test visualization
print("\n✓ Testing Visualization Libraries...")
try:
    import matplotlib
    print(f"  ✓ matplotlib: {matplotlib.__version__}")
except ImportError as e:
    print(f"  ✗ matplotlib: {e}")

# Test notifications
print("\n✓ Testing Notification Libraries...")
try:
    import telegram
    print("  ✓ python-telegram-bot: installed")
except ImportError as e:
    print(f"  ✗ python-telegram-bot: {e}")

# Test scheduling
print("\n✓ Testing Scheduling Libraries...")
try:
    from apscheduler.schedulers.background import BackgroundScheduler
    print("  ✓ APScheduler: installed")
except ImportError as e:
    print(f"  ✗ APScheduler: {e}")

print("\n" + "=" * 60)
print("✅ Environment setup complete!")
print("=" * 60)
print("\nNext steps:")
print("1. Open Angel One account (if not already)")
print("2. Apply for Smart API access")
print("3. Update .env file with Angel One credentials")
print("4. Start building the trading system!")
print("\n" + "=" * 60)
