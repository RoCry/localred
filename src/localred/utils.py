import logging
import os
from typing import Optional
from urllib.parse import quote

# Setup logging
logger = logging.getLogger("localred")
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(handler)

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
try:
    logger.setLevel(getattr(logging, log_level))
except AttributeError:
    logger.warning(f"Invalid log level '{log_level}', defaulting to INFO")
    logger.setLevel(logging.INFO)
logger.propagate = False  # Prevent duplicate logging


def build_search_url(query: Optional[str]) -> str:
    if not query:
        return "https://www.xiaohongshu.com/explore?channel_type=web_note_detail_r10"
    return f"https://www.xiaohongshu.com/search_result?keyword={quote(query)}&source=web_explore_feed"


def load_js_file(filename: str) -> None:
    if not filename.endswith(".js"):
        filename += ".js"
    fp = os.path.join(os.path.dirname(__file__), "js", filename)
    with open(fp, "r") as f:
        return f.read()
