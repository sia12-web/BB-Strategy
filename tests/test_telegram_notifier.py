"""Tests for TelegramNotifier class."""

import pytest
from unittest.mock import patch, MagicMock
from bb_strategy.notifications.telegram_notifier import TelegramNotifier

@patch("requests.post")
def test_send_signal_calls_correct_url(mock_post):
    """Verify that send_signal calls the correct Telegram API URL and payload."""
    notifier = TelegramNotifier(token="bot123", chat_id="chat456")
    notifier.send_signal(
        pair="EUR_USD",
        direction="long",
        entry=1.0842,
        sl=1.0821,
        tp=1.0871,
        mode="paper"
    )
    
    expected_url = "https://api.telegram.org/botbot123/sendMessage"
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == expected_url
    assert kwargs["json"]["chat_id"] == "chat456"
    assert "<b>EUR_USD LONG</b>" in kwargs["json"]["text"]
    assert "Mode: PAPER" in kwargs["json"]["text"]

@patch("requests.post")
def test_failure_does_not_raise(mock_post):
    """Failure in requests.post should not raise an exception."""
    mock_post.side_effect = ConnectionError("Network down")
    notifier = TelegramNotifier(token="bot123", chat_id="chat456")
    
    # Should not raise
    notifier.send_error("Test error")
    mock_post.assert_called_once()

@patch("requests.post")
def test_disabled_when_token_none(mock_post):
    """Notification methods should do nothing if token is None."""
    notifier = TelegramNotifier(token=None, chat_id="chat456")
    notifier.send_signal("EUR_USD", "long", 1.0, 0.9, 1.1, "paper")
    mock_post.assert_not_called()

def test_notifier_enabled_logic():
    """Verify enabled flag logic."""
    assert TelegramNotifier(token="a", chat_id="b").enabled is True
    assert TelegramNotifier(token=None, chat_id="b").enabled is False
    assert TelegramNotifier(token="a", chat_id=None).enabled is False
