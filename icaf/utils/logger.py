import logging
from pathlib import Path

from icaf.config.settings import settings


def setup_logger():
    """
    Initialize the global TCAF logger.
    Creates logs/tcaf.log immediately so the file always exists.
    """
    log_dir = settings.LOG_DIR
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "tcaf.log"
    log_file.touch(exist_ok=True)   # ← ensures file exists even before first write

    logger = logging.getLogger("tcaf")
    logger.setLevel(settings.LOG_LEVEL)

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    )

    # File handler — global log
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger


def attach_run_log(run_dir: str) -> None:
    """
    Call this once the run directory is known.
    Adds a second FileHandler so all subsequent log lines also go to
    <run_dir>/tcaf.log alongside the global logs/tcaf.log.
    """
    run_log = Path(run_dir) / "tcaf.log"
    run_log.parent.mkdir(parents=True, exist_ok=True)
    run_log.touch(exist_ok=True)

    logger = logging.getLogger("tcaf")
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    )

    # Avoid adding duplicate run-level handlers on re-runs in the same process
    existing_paths = {
        h.baseFilename for h in logger.handlers
        if isinstance(h, logging.FileHandler)
    }
    if str(run_log.resolve()) not in existing_paths:
        run_handler = logging.FileHandler(run_log)
        run_handler.setFormatter(formatter)
        logger.addHandler(run_handler)


logger = setup_logger()