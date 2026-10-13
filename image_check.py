#!/usr/bin/env python3
"""One cheap image call to see what the OpenAI image API says right now.

Run from Actions -> Image check. The result shows on the run page.
"""
import os
import time

import openai

from config import OPENAI_IMAGE_MODEL


def main():
    client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=180, max_retries=0)
    t = time.time()
    try:
        r = client.images.generate(model=OPENAI_IMAGE_MODEL, prompt="A plain baseball on grass.",
                                   size="1024x1024", quality="low", n=1)
        kind = "base64" if getattr(r.data[0], "b64_json", None) else "url"
        print(f"::notice::Image API OK with {OPENAI_IMAGE_MODEL} in {time.time() - t:.0f}s ({kind})")
    except Exception as e:
        status = getattr(e, "status_code", "")
        print(f"::error::Image API failed after {time.time() - t:.0f}s: {type(e).__name__} {status}: {str(e)[:400]}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
