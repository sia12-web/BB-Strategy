"""Entry point for the live signal engine.

Loads trade modes, starts SignalMonitor, and routes signals to
live orders or paper trades based on per-pair mode + env gate.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import colorama
import jsonlines

from bb_strategy.config import Config
from bb_strategy.live.candle_fetcher import CandleFetcher
from bb_strategy.live.order_executor import OrderExecutor
from bb_strategy.live.startup_check import run_startup_check
from bb_strategy.live.performance_tracker import PerformanceTracker
from bb_strategy.live.signal_monitor import SignalMonitor
from bb_strategy.live.trade_mode import get_trade_modes
from bb_strategy.notifications.telegram_notifier import TelegramNotifier
from bb_strategy.strategy.position_sizer import PositionSizer

# ── Logging ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
SIGNAL_LOG_PATH = DATA_DIR / "signal_log.jsonl"
OPTIMIZATION_RESULTS_PATH = DATA_DIR / "optimization_results.json"

# ── Constants ────────────────────────────────────────────────────────

DEFAULT_BALANCE = 10_000.0
DEFAULT_RISK_PCT = 0.01  # 1%
POLL_INTERVAL = 60  # seconds


def _log_signal(entry: dict) -> None:
    """Append a signal entry to signal_log.jsonl."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with jsonlines.open(str(SIGNAL_LOG_PATH), mode="a") as writer:
        writer.write(entry)


def _print_alert(pair: str, signal: int, entry_price: float,
                 stop_loss: float, take_profit: float, mode: str) -> None:
    """Print a colored console alert."""
    direction = "LONG" if signal == 1 else "SHORT"

    if mode == "paper":
        color = colorama.Fore.YELLOW
        mode_label = "PAPER"
    elif signal == 1:
        color = colorama.Fore.GREEN
        mode_label = "LIVE"
    else:
        color = colorama.Fore.RED
        mode_label = "LIVE"

    alert = (
        f"{color}"
        f"[{pair}] [{direction}] @ {entry_price:.5f} "
        f"| SL: {stop_loss:.5f} | TP: {take_profit:.5f} "
        f"| Mode: {mode_label}"
        f"{colorama.Style.RESET_ALL}"
    )
    print(alert)


def build_signal_handler(
    config: Config,
    trade_modes: dict[str, str],
    executor: OrderExecutor,
    sizer: PositionSizer,
    balance: float = DEFAULT_BALANCE,
    risk_pct: float = DEFAULT_RISK_PCT,
    notifier: Optional[TelegramNotifier] = None,
):
    """Return a callback for SignalMonitor.on_signal."""

    def handle_signal(pair: str, signal: int, row) -> None:
        entry_price = float(row.get("entry_price", row.get("close", 0)))
        stop_loss = float(row.get("stop_loss", 0))
        take_profit = float(row.get("take_profit", 0))

        if entry_price == 0 or stop_loss == 0:
            logger.warning("Invalid prices for %s signal — skipping", pair)
            return

        # Calculate position size
        try:
            units = sizer.calculate(
                account_balance=balance,
                risk_pct=risk_pct,
                entry_price=entry_price,
                stop_loss=stop_loss,
                pair=pair,
            )
        except ValueError as exc:
            logger.error("Position sizing failed for %s: %s", pair, exc)
            return

        pair_mode = trade_modes.get(pair, "paper")
        env_is_live = config.OANDA_ENV == "live"

        # Dual gate: both env AND pair mode must be "live"
        effective_mode = "live" if (env_is_live and pair_mode == "live") else "paper"

        # Build log entry
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pair": pair,
            "signal": signal,
            "direction": "long" if signal == 1 else "short",
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "units": units,
            "pair_mode": pair_mode,
            "env": config.OANDA_ENV,
            "effective_mode": effective_mode,
        }

        # Log BEFORE executing (security requirement)
        _log_signal(log_entry)

        # Console alert
        _print_alert(pair, signal, entry_price, stop_loss, take_profit, effective_mode)

        # Execute
        if effective_mode == "live":
            try:
                result = executor.place_live_order(
                    pair=pair,
                    signal=signal,
                    entry_price=entry_price,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    units=units,
                )
                log_entry["order_result"] = result
            except Exception:
                logger.exception("Live order FAILED for %s", pair)
                log_entry["order_result"] = {"status": "error"}
        else:
            executor.record_paper_trade(
                pair=pair,
                signal=signal,
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                units=units,
            )
            log_entry["order_result"] = {"status": "paper_recorded"}

        # Log outcome
        _log_signal(log_entry)

        # Telegram Notification
        if notifier:
            direction = "long" if signal == 1 else "short"
            notifier.send_signal(
                pair=pair,
                direction=direction,
                entry=entry_price,
                sl=stop_loss,
                tp=take_profit,
                mode=effective_mode
            )

    return handle_signal


def main() -> None:
    """Start the live signal engine."""
    colorama.init()

    config = Config()
    
    # Initialize Notifier (gracefully disabled if token/chat_id missing)
    notifier = TelegramNotifier(
        token=config.TELEGRAM_BOT_TOKEN,
        chat_id=config.TELEGRAM_CHAT_ID,
        signal_log_path=SIGNAL_LOG_PATH,
    )

    # Phase 12: Startup Checks
    if not run_startup_check():
        msg = "Startup checks failed. Aborting engine launch."
        logger.error(msg)
        notifier.send_error(msg)
        sys.exit(1)

    logger.info("Starting live signal engine — env=%s", config.OANDA_ENV)
    logger.info("Pairs: %s", config.PAIRS)

    # Load trade modes
    trade_modes = get_trade_modes(OPTIMIZATION_RESULTS_PATH, pairs=config.PAIRS)
    for pair, mode in trade_modes.items():
        logger.info("  %s → %s", pair, mode.upper())

    # Warn if env is live
    if config.OANDA_ENV == "live":
        logger.warning("⚠️  LIVE TRADING ENABLED — real money at risk!")
    else:
        logger.info("Practice mode — no real orders will be placed")

    # Build components
    executor = OrderExecutor(config=config)
    sizer = PositionSizer()
    fetcher = CandleFetcher()

    # Build signal handler
    handler = build_signal_handler(
        config=config,
        trade_modes=trade_modes,
        executor=executor,
        sizer=sizer,
        notifier=notifier,
    )

    # Startup Notification
    validated_pairs = [p for p, m in trade_modes.items() if m == "live" or p == "EUR_USD"]
    mode = "live" if config.OANDA_ENV == "live" else "paper"
    notifier.send_startup(validated_pairs, mode=mode)

    # Phase 12: Performance Tracking Wrapper
    tracker = PerformanceTracker(config=config)
    paper_trades_path = config.DATA_DIR / "paper_trades.json"

    def extended_handler(pair: str, signal: int, row) -> None:
        handler(pair, signal, row)
        # Check if we should update performance metrics
        if paper_trades_path.exists():
            try:
                with open(paper_trades_path, "r", encoding="utf-8") as f:
                    p_trades = json.load(f)
                if len(p_trades) >= 5:
                    tracker.update(paper_trades_path)
            except Exception:
                pass

    # Start monitor
    monitor = SignalMonitor(
        pairs=config.PAIRS,
        poll_interval_seconds=POLL_INTERVAL,
        candle_fetcher=fetcher,
        on_signal=extended_handler,
    )

    try:
        monitor.run()
    except KeyboardInterrupt:
        logger.info("Signal engine stopped by user")
        sys.exit(0)


if __name__ == "__main__":
    main()
