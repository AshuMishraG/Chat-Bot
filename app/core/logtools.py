import time
import logging
from contextlib import contextmanager
from pythonjsonlogger.json import JsonFormatter

logger = logging.getLogger(__name__)


class CustomJsonFormatter(JsonFormatter):
    """
    Custom JSON formatter that correctly handles uvicorn's access logs.
    """

    def add_fields(self, log_record, record, message_dict):
        """
        This method is called by the parent class to add fields to the log record.
        We are extending it to include the uvicorn access log fields.
        """
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)

        if (
            record.name == "uvicorn.access"
            and isinstance(record.args, tuple)
            and len(record.args) == 5
        ):
            client_addr, method, full_path, http_version, status_code = record.args
            log_record["client_addr"] = client_addr
            log_record["request_line"] = f"{method} {full_path} HTTP/{http_version}"
            log_record["status_code"] = status_code

@contextmanager
def log_execution_time(description: str):
    """A context manager to log the execution time of a code block."""
    start_time = time.perf_counter()
    try:
        yield
    finally:
        duration = time.perf_counter() - start_time
        logger.info(f"{duration:.4f} seconds for {description}")
