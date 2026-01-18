import anyio
from openai import AsyncOpenAI

from pg_mcp.config import Settings


async def main() -> None:
    settings = Settings()
    cfg = settings.openai
    client = AsyncOpenAI(
        api_key=cfg.api_key.get_secret_value(),
        timeout=cfg.timeout,
        base_url=cfg.base_url,
    )
    print(f"Using base_url: {client.base_url!r}")
    print(f"Using model: {cfg.model!r}")
    try:
        resp = await client.chat.completions.create(
            model=cfg.model,
            messages=[{"role": "user", "content": "Say hello"}],
            max_tokens=16,
        )
        content = resp.choices[0].message.content
        print("Call succeeded, response snippet:")
        print(content[:200])
    except Exception as e:
        print("Call failed:", type(e).__name__, "-", e)


if __name__ == "__main__":
    anyio.run(main)
