import os
import platform


class BrowserNotFoundError(Exception):
    pass


CHROME_PATHS = {
    "Darwin": [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ],
}


def find_chrome() -> str:
    system = platform.system()
    if system not in CHROME_PATHS:
        raise BrowserNotFoundError(f"Unsupported platform: {system}")
    for path in CHROME_PATHS[system]:
        if os.path.exists(path):
            return path
    raise BrowserNotFoundError("Cannot find a chrome-based browser on your system")
