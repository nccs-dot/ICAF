from pathlib import Path


class Settings:

    # Project root
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Output directories
    OUTPUT_DIR = BASE_DIR / "output"
    LOG_DIR = BASE_DIR / "logs"

    # Logging
    LOG_LEVEL = "INFO"

    # SSH
    SSH_TIMEOUT = 10

    # Framework metadata
    FRAMEWORK_NAME = "TCAF"
    FRAMEWORK_FULL_NAME = "Telecom Compliance Automation Framework"
    VERSION = "0.1"


settings = Settings()

def initialize_directories():
    directories = [
        settings.OUTPUT_DIR,
        settings.LOG_DIR,
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
