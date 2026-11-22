"""Uvicorn's log formatters, stamping each line with the time in UTC."""

import time

from uvicorn.logging import AccessFormatter, DefaultFormatter


class UtcDefaultFormatter(DefaultFormatter):
    """The server's messages, such as startup and errors."""

    converter = time.gmtime


class UtcAccessFormatter(AccessFormatter):
    """One line per request."""

    converter = time.gmtime
