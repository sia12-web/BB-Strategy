"""Keep-alive wrapper for the live trading engine."""

import os
import sys
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Setup simple logging for the keep-alive script
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
LOG_FILE = DATA_DIR / "keep_alive.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [KEEP-ALIVE] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

MAX_RESTARTS = 10
RESTART_DELAY = 10  # Seconds

def run_loop():
    """Run the live engine in a loop, restarting on crashes."""
    restart_count = 0
    cmd = [sys.executable, "-m", "bb_strategy.live.run_live"]
    
    logger.info("Starting keep-alive loop for: %s", " ".join(cmd))
    
    while restart_count <= MAX_RESTARTS:
        start_time = datetime.now()
        
        try:
            # Run the process and wait for it to finish
            result = subprocess.run(cmd, check=False)
            
            if result.returncode == 0:
                logger.info("Signal engine stopped cleanly (return code 0). Exiting loop.")
                break
            elif result.returncode == 1:
                # Code 1 is often our deliberate startup exit
                logger.error("Signal engine exited with code 1 (Potential configuration/startup error).")
            else:
                logger.error("Signal engine crashed with exit code %s", result.returncode)
                
        except Exception as e:
            logger.error("Error executing subprocess: %s", e)
        
        # If it ran for less than 60 seconds, it's a rapid crash
        duration = (datetime.now() - start_time).total_seconds()
        if duration < 60:
            restart_count += 1
            logger.warning("Rapid crash detected (duration: %.1fs). Restart count: %d/%d", 
                           duration, restart_count, MAX_RESTARTS)
        else:
            # Reset restart count if it was stable for at least a minute
            if restart_count > 0:
                logger.info("Stability reset: internal was stable for %.1fs. Resetting restart counter.", duration)
            restart_count = 0

        if restart_count > MAX_RESTARTS:
            logger.error("Max restarts exceeded. Giving up.")
            # Send Telegram error if configured
            load_dotenv()
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("TELEGRAM_CHAT_ID")
            if token and chat_id:
                try:
                    from bb_strategy.notifications.telegram_notifier import TelegramNotifier

                    notifier = TelegramNotifier(token=token, chat_id=chat_id)
                    notifier.send_error(
                        f"Keep-alive stopped after {MAX_RESTARTS} restarts. Engine crashed repeatedly."
                    )
                except Exception:
                    logger.exception("Failed to send Telegram error on max restarts")
            sys.exit(1)

        logger.info("Restarting in %d seconds...", RESTART_DELAY)
        time.sleep(RESTART_DELAY)

if __name__ == "__main__":
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    try:
        run_loop()
    except KeyboardInterrupt:
        logger.info("Keep-alive loop stopped by user.")
        sys.exit(0)
