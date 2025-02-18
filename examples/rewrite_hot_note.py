import fire
from smolllm import ask_llm

from localred.client import BrowserClient
from localred.models import Note


def _notes_to_str(notes: list[Note]) -> str:
    return "\n".join([note.to_md() for note in notes])


async def get_top_notes(limit: int = 1, headless: bool = True) -> list[Note]:
    async with BrowserClient(remote_debugging_port=None, headless=headless) as client:
        results = await client.search(None, max_results=limit, visit_links=True)
        return results


async def rewrite_notes(notes_str: str) -> str:
    prompt = f"""你现在是一个文案模仿大师，需要对我提供给你的文章进行仿写； 总结我的文案的语言风格和逻辑结构； 风格与之前的文案保持一致、字数在500字左右、逻辑不能有太大出入。
文章：
{notes_str}
"""
    result = await ask_llm(prompt)
    return result


async def run(limit: int = 5, headless: bool = True):
    notes = await get_top_notes(limit, headless)
    notes_str = _notes_to_str(notes)
    print(notes_str)
    print("-" * 100)
    result = await rewrite_notes(notes_str)
    print(result)


if __name__ == "__main__":
    fire.Fire(run)
