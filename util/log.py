from datetime import datetime
from enum import Enum


class LogTag(str, Enum):
    INFO = "INFO"
    DEBUG = "DEBUG"
    WARNING = "WARNING"
    ERROR = "ERROR"


# Fixed widths
TAG_WIDTH = 7   # adjust if you add longer tags


def log(message: str, tag: LogTag = LogTag.INFO) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Pad tag to fixed width (left-aligned)
    tag_str = f"{tag.value:<{TAG_WIDTH}}"

    print(f"{timestamp} [{tag_str}] | {message}")