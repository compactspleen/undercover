import json
import logging
from logging.config import DictConfigurator
from pathlib import Path

import pytest

LOG_CONFIG = Path(__file__).parents[1] / "log_config.json"
# 2026-11-22T09:30:05.250Z
MOMENT = 1795339805.25
REQUEST = ("127.0.0.1:5173", "GET", "/api/claims/CLM-1001", "1.1", 200)


def format_line(formatter_name: str, message: str, args: tuple[object, ...]) -> str:
    configurator = DictConfigurator(json.loads(LOG_CONFIG.read_text()))
    formatter = configurator.configure_formatter(
        configurator.config["formatters"][formatter_name]
    )
    record = logging.LogRecord("uvicorn", logging.INFO, "", 0, message, args, None)
    record.created = MOMENT
    record.msecs = 250.0
    return formatter.format(record)


@pytest.mark.parametrize(
    ("formatter_name", "message", "args"),
    [
        ("default", "Application startup complete.", ()),
        ("access", '%s - "%s %s HTTP/%s" %d', REQUEST),
    ],
)
def test_each_log_line_starts_with_the_time_in_utc(
    formatter_name: str, message: str, args: tuple[object, ...]
):
    line = format_line(formatter_name, message, args)
    assert line.startswith("2026-11-22T09:30:05.250Z INFO:")


def test_a_request_line_keeps_the_request_and_status():
    line = format_line("access", '%s - "%s %s HTTP/%s" %d', REQUEST)
    assert '127.0.0.1:5173 - "GET /api/claims/CLM-1001 HTTP/1.1" 200' in line
