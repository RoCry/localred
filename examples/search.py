import os
from datetime import datetime
from pathlib import Path
from time import time
from typing import Optional

import fire

from localred.client import BrowserClient

# Constants
OUTPUT_DIR = Path("./outputs/")
CONTENT_PREVIEW_LIMIT = 500


async def run_search(
    query: Optional[str] = None,
    limit: int = 5,
    visit: bool = False,
    headless: bool = True,
    remote_debugging_port: int = 0,
    browser_state_path: str | None = None,
):
    output_dir = OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    async with BrowserClient(
        remote_debugging_port=remote_debugging_port,
        headless=headless,
        browser_state_path=browser_state_path,
    ) as client:
        start_time = time()
        results = await client.search(query, max_results=limit, visit_links=visit)
        end_time = time()

        # Process and save results
        for result in results:
            # Print preview
            print("\n" + "-" * 70)
            print(result.to_md(truncate_num=CONTENT_PREVIEW_LIMIT))
            print("-" * 40)

            # Save full content to file if it's a detailed result
            if result.content and len(result.content) > CONTENT_PREVIEW_LIMIT:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_filename = "".join(
                    c if c.isalnum() else "_" for c in result.url.split("//")[-1]
                )
                output_file = output_dir / f"{safe_filename[:60]}_{timestamp}.md"

                # Save full content
                output_file.write_text(result.content)
                print(f"\nFull content saved to: {output_file}")

        print(f"\nTotal results: {len(results)}")
        print(f"Total time taken: {end_time - start_time:.2f}s")


if __name__ == "__main__":
    fire.Fire(run_search)
