import logging
import os

from rich.logging import RichHandler

logger = logging.getLogger("cxstat")
FORMAT = "%(message)s"
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "WARNING"),
    format=FORMAT,
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)],
)
