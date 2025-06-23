
import re
import logging
import inspect
import traceback

from datetime import datetime
from rich.console import Console
from rich.traceback import Traceback
# from nethawk.helper.utilities import get_nethawk_dir, generate_object

console = Console()

NOTICE = 25
SUCCESS = 60
FNC = 15  # New level for function calls
logging.addLevelName(NOTICE, "LOG")
logging.addLevelName(SUCCESS, "SUC")
# logging.addLevelName(FNC, "FNC")  # Register the FNC level

LEVEL_TAGS = {
    logging.DEBUG: "DBG",
    logging.INFO: "INF",
    NOTICE: "LOG",
    logging.WARNING: "WRN",
    logging.ERROR: "ERR",
    logging.CRITICAL: "CRT",
    SUCCESS: "SUC",
    # FNC: "FNC",  # Add the FNC tag
}

LEVEL_STYLES = {
    "DBG": "yellow reverse",
    "INF": "blue",
    "LOG": "cyan",
    "WRN": "yellow",
    "ERR": "red",
    "CRT": "red reverse",
    "SUC": "green",
    "FNC": "magenta",  # Style for function calls
}

# suppress third-party logs if needed:
for noisy_logger in ["httpx", "urllib3", "requests", "httpcore", "pymongo", "mongoengine", "scrapy", "charset_normalizer", "chardet"]:
    logging.getLogger(noisy_logger).setLevel(logging.CRITICAL + 1)

def strip_markup(text: str) -> str:
    """Remove Rich markup tags from a string."""
    return re.sub(r"\[/?[^\]]+\]", "", text)

class RichConsoleHandler(logging.Handler):
    """Custom handler to output styled logs to the console."""

    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        
    def emit(self, record):
        try:
            # Get the tag and style based on the log level
            tag = LEVEL_TAGS.get(record.levelno, "LOG")
            style = LEVEL_STYLES.get(tag, "white")
            message = record.getMessage()

            # Print the styled log message
            console.print(f"[bold][[{style}]{tag}[/]][/] {message}")

            # Only print full traceback in DEBUG mode
            if record.exc_info and record.levelno <= logging.DEBUG:
                # If an exception is associated, render the traceback
                exc_type, exc_value, exc_tb = record.exc_info

                # Ensure that exc_type and exc_value are not None
                if exc_type and exc_value:
                    trace = Traceback.from_exception(exc_type, exc_value, exc_tb, show_locals=True)
                    console.print(trace)
                else:
                    console.print("[red]Error: Missing exception details[/]")

        except Exception:
            self.handleError(record)

class FileFormatter(logging.Formatter):
    """Formatter that strips Rich markup for file logging."""
    def format(self, record):
        clean_message = strip_markup(record.getMessage())
        level_tag = LEVEL_TAGS.get(record.levelno, record.levelname)
        return f"[{self.formatTime(record, self.datefmt)}] [{level_tag}] {clean_message}"

def setup_logging(verbose: bool = False, debug: bool = False) -> logging.Logger:
    """Initialize and configure logging to console and file."""
    # logfile_path = LOGS_DIR / f"log_{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.log"

    # Console handler
    console_handler = RichConsoleHandler()

    # Set console handler levels to ensure INFO and SUCCESS messages always appear
    if debug:
        console_handler.setLevel(logging.DEBUG)  # Show DEBUG and above when debug is True
    elif verbose:
        console_handler.setLevel(logging.INFO)  # Show INFO and above when verbose is True
    else:
        # Ensure INFO and SUCCESS show up regardless of verbose/debug setting
        console_handler.setLevel(logging.INFO)  # Show INFO and above by default

    # # File handler (always log at DEBUG level)
    # file_handler = logging.FileHandler(logfile_path, encoding="utf-8")
    # file_handler.setLevel(logging.DEBUG)
    # file_handler.setFormatter(FileFormatter(datefmt="%Y-%m-%d %H:%M:%S"))

    # Root logger configuration (always log at DEBUG level)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)
    # root_logger.addHandler(file_handler)
    root_logger.propagate = False

    # Extend Logger with custom methods
    def log(self, message, *args, **kwargs):
        # Always log NOTICE (LOG) level if verbose is True
        if verbose and self.isEnabledFor(NOTICE):
            self._log(NOTICE, message, args, kwargs)

    def info(self, message, *args, **kwargs):
        # Ensure INFO messages always show up
        if self.isEnabledFor(logging.INFO):
            self._log(logging.INFO, message, args, kwargs)

    def success(self, message, *args, **kwargs):
        if self.isEnabledFor(SUCCESS):
            self._log(SUCCESS, message, args, kwargs)
            
    logging.Logger.log = log # type: ignore
    logging.Logger.info = info # type: ignore
    logging.Logger.success = success # type: ignore
    # logging.Logger.func = func # type: ignore

    return root_logger


# Example of function to be logged with FNC tag
# def is_live(host, max_tries=3, timeout=2, test='test'):
#     """ 
#     Check if host is live using ping3.
#     """
#     # Log the function call
#     # logging.getLogger().func()

#     # Function logic here
#     print(f"Checking if host {host} is live with max_tries={max_tries} and timeout={timeout}")

# # Example of use
# if __name__ == "__main__":
#     # Test with verbose=False and debug=True, ensure INFO and SUCCESS always show
#     logger = setup_logging(target="test_target", verbose=False, debug=True)

#     logger.info("Starting scan...")  # This should now always show
#     logger.warning("Port [bold blue]80[/] is filtered, skipping...")  # Should show on default logging level
#     logger.debug("Internal state: hostname=None")  # Should not show
#     logger.error("Failed to connect to target")  # Should show
#     logger.success("Scan completed successfully!")  # Should show
#     logger.log(f"This is a regular log message")  # Should show only if verbose=True
#     logger.critical("Critical failure encountered", exc_info=False)  # Should show

#     # Call the is_live function to see FNC logs
#     is_live("83.136.255.10", max_tries=3, timeout=2)
