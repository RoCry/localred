import os
from datetime import datetime
from pathlib import Path
from time import time

import fire

from localred.client import BrowserClient

testing_link = "https://www.xiaohongshu.com/explore/6797ca340000000028029b30?xsec_token=ABSVKhdBr5QKb8jSfUvUufCB2S_XeBzBngsNTGIUKk7bw=&xsec_source=pc_feed"

# Constants
OUTPUT_DIR = Path("./outputs/")
CONTENT_PREVIEW_LIMIT = 500


async def run_visit(
    link: str = testing_link,
    remote_debugging_port: int = 0,
    headless=True,
):
    output_dir = OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    async with BrowserClient(
        remote_debugging_port=remote_debugging_port, headless=headless
    ) as client:
        start_time = time()
        results = await client.visit_links([link])
        end_time = time()

        # Process and save results
        for result in results:
            # Print preview
            print("\n" + "-" * 70)
            print(result.to_md(truncate_num=CONTENT_PREVIEW_LIMIT))
            print("-" * 40)

            if len(result.content) > CONTENT_PREVIEW_LIMIT:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_filename = "".join(
                    c if c.isalnum() else "_" for c in result.url.split("//")[-1]
                )
                output_file = output_dir / f"{safe_filename[:60]}_{timestamp}.md"

                # Save full content
                output_file.write_text(result.content)
                print(f"\nFull content saved to: {output_file}")

        print(f"Total time taken: {end_time - start_time:.2f}s")


if __name__ == "__main__":
    fire.Fire(run_visit)
