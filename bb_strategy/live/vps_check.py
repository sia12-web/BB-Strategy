"""System readiness report for VPS deployment."""

import os
import sys
import logging
import importlib
from pathlib import Path

# Required packages to check
REQUIRED_PKGS = [
    "oandapyV20", "pandas", "pyarrow", "dotenv", "pytest", 
    "plotly", "jinja2", "schedule", "colorama", "jsonlines", 
    "tabulate", "requests"
]

REQUIRED_ENV_KEYS = [
    "OANDA_API_KEY", "OANDA_ACCOUNT_ID", "OANDA_ENV"
]

def run_vps_check() -> int:
    """Print readiness report. Returns 0 on success, 1 on failure."""
    print("--- VPS READINESS CHECK ---")
    failed = False

    # 1. Python version
    py_ver = sys.version_info
    if py_ver.major == 3 and py_ver.minor >= 11:
        print(f"PASS: Python version {py_ver.major}.{py_ver.minor}")
    else:
        print(f"FAIL: Python version {py_ver.major}.{py_ver.minor} (needs >= 3.11)")
        failed = True

    # 2. Package imports
    missing_pkgs = []
    for pkg in REQUIRED_PKGS:
        # Map library names to import names if different
        import_name = "dotenv" if pkg == "python-dotenv" else pkg
        try:
            importlib.import_module(import_name)
        except ImportError:
            missing_pkgs.append(pkg)
    
    if not missing_pkgs:
        print("PASS: All required packages importable")
    else:
        print(f"FAIL: Missing packages: {missing_pkgs}")
        failed = True

    # 3. Environment file
    root = Path(__file__).resolve().parent.parent.parent
    env_path = root / ".env"
    if env_path.exists():
        print(f"PASS: .env file found at {env_path}")
        # Check keys
        from dotenv import load_dotenv
        load_dotenv(env_path)
        missing_keys = [k for k in REQUIRED_ENV_KEYS if not os.getenv(k)]
        if not missing_keys:
            print("PASS: All required environment keys present")
        else:
            print(f"FAIL: Missing environment keys: {missing_keys}")
            failed = True
    else:
        print("FAIL: .env file not found")
        failed = True

    # 4. Data directory
    data_dir = root / "data"
    if data_dir.exists():
        print(f"PASS: Data directory found at {data_dir}")
        # Permissions
        if os.access(data_dir, os.W_OK):
            print("PASS: Write permissions on data/ verified")
        else:
            print("FAIL: No write permissions on data/")
            failed = True
            
        # 3y Parquet files (parity check)
        missing_data = []
        for pair in ["EUR_USD"]:
            for tf in ["M15", "H1"]:
                p = data_dir / f"{pair}_{tf}_3y.parquet"
                if not p.exists():
                    missing_data.append(str(p.name))
        
        if not missing_data:
            print("PASS: Historical 3y parquet files verified")
        else:
            print(f"FAIL: Missing historical data: {missing_data}")
            failed = True
    else:
        print("FAIL: Data directory not found")
        failed = True

    print("-" * 30)
    if failed:
        print("SYSTEM NOT READY FOR VPS DEPLOYMENT")
        return 1
    
    print("SYSTEM READY FOR VPS DEPLOYMENT")
    return 0

if __name__ == "__main__":
    sys.exit(run_vps_check())
