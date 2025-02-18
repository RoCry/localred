import io
import os

import fire
from PIL import Image

from localred.client import BrowserClient


async def display_qrcode(img_bytes: bytes):
    """Display QR code in terminal using qrcode_terminal."""
    # Store the QR code temporarily
    temp_path = os.path.join(os.path.expanduser("/tmp"), "localred_login_qr.png")
    img = Image.open(io.BytesIO(img_bytes))
    img.save(temp_path)

    print(f"QR code saved to: {temp_path}")

    # Try to open the image automatically if on macOS and not in SSH session
    try:
        is_ssh = (
            "SSH_CONNECTION" in os.environ
            or "SSH_CLIENT" in os.environ
            or "SSH_TTY" in os.environ
        )
        if os.path.exists("/usr/bin/open") and not is_ssh:
            os.system(f"open {temp_path}")
    except Exception:
        pass


async def main(
    remote_debugging_port: int = 9222,
    timeout: float = 120,
):
    print(f"Connecting to Chrome on port {remote_debugging_port}...")
    async with BrowserClient(remote_debugging_port=remote_debugging_port) as client:
        success = await client.try_login(display_qrcode, timeout)
        if success:
            print("Login successful! You can now use the client for other operations.")
        else:
            print("Login failed.")


if __name__ == "__main__":
    fire.Fire(main)
