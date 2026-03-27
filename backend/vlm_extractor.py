import openai
import json
import os
from pathlib import Path

client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = Path("prompts/macro_extraction.txt").read_text()


async def extract_macro_features(b64_image: str) -> dict:
    """
    Calls GPT-4o-mini with a strictly constrained system prompt.
    The model is forbidden from naming any medication.
    Returns only {color, shape, scoring} as structured JSON.
    """
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}",
                            "detail": "low"
                        }
                    },
                    {
                        "type": "text",
                        "text": "Analyze this pill image and return only the JSON object described in your instructions."
                    }
                ]
            }
        ],
        max_tokens=150,
        temperature=0.0,
        response_format={"type": "json_object"}
    )

    raw = response.choices[0].message.content
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"color": "unknown", "shape": "unknown", "scoring": "unknown", "error": raw}
