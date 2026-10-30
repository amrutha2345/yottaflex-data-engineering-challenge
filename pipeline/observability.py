import json
import logging
from datetime import datetime, timezone
from pathlib import Path


def setup_logging(output_dir: str | Path) -> logging.Logger:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("yottaflex_pipeline")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Avoid duplicate handlers if setup is called more than once.
    if logger.handlers:
        return logger

    formatter = logging.Formatter("%(message)s")

    file_handler = logging.FileHandler(
        output_dir / "pipeline.log", encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def log_event(logger: logging.Logger, event: str, **fields) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        **fields,
    }
    logger.info(json.dumps(record, default=str))
