"""Test connectivity to all configured model providers."""
import asyncio
import os
import sys
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

TEST_PROMPT = "Respond with only the word: OK"

providers = [
    {
        "name": "GPT-5.5 (aixor.org)",
        "api_base": os.getenv("OPENAI_BASE_URL", ""),
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "model": "gpt-5.5",
    },
    {
        "name": "DeepSeek-V4-Pro (deepseek.com)",
        "api_base": os.getenv("DEEPSEEK_BASE_URL", ""),
        "api_key": os.getenv("DEEPSEEK_API_KEY", ""),
        "model": "deepseek-v4-pro",
    },
    {
        "name": "OpenRouter (google/gemma-2-9b-it)",
        "api_base": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "model": "google/gemma-4-31b-it:free",
    },
]


async def test_provider(p: dict) -> dict:
    if not p["api_key"] or p["api_key"] == "sk-your-key":
        return {**p, "status": "SKIP", "error": "API key not configured"}

    client = AsyncOpenAI(base_url=p["api_base"], api_key=p["api_key"], timeout=30.0)
    try:
        start = asyncio.get_event_loop().time()
        response = await client.chat.completions.create(
            model=p["model"],
            messages=[{"role": "user", "content": TEST_PROMPT}],
            temperature=0.0,
            max_tokens=50,
        )
        elapsed = asyncio.get_event_loop().time() - start
        content = response.choices[0].message.content.strip()
        return {
            **p,
            "status": "OK" if content == "OK" else "CONTENT_MISMATCH",
            "elapsed": f"{elapsed:.1f}s",
            "response": content,
        }
    except Exception as e:
        return {**p, "status": "FAIL", "error": str(e)}


async def main():
    print("=" * 60)
    print("  Model/Provider Connectivity Test")
    print("=" * 60)
    print()

    results = await asyncio.gather(*[test_provider(p) for p in providers])

    all_ok = True
    for r in results:
        status_icon = {"OK": "PASS", "SKIP": "SKIP"}.get(r["status"], "FAIL")
        print(f"  [{status_icon:5s}] {r['name']}")
        print(f"          Model: {r['model']}")
        print(f"          API:   {r['api_base']}")
        if r["status"] == "OK":
            print(f"          Time:  {r['elapsed']}")
        elif r["status"] == "SKIP":
            print(f"          Info:  {r['error']}")
        else:
            print(f"          Error: {r.get('error', 'unknown')}")
            all_ok = False
        print()

    print("=" * 60)
    if all_ok:
        print("  All active providers connected successfully!")
    else:
        print("  Some providers failed - check errors above.")
    print("=" * 60)

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
