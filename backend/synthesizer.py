import openai
import os
from pathlib import Path

client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYNTHESIS_PROMPT = Path("prompts/synthesis_formatter.txt").read_text()


async def synthesize_response(drug_data: dict) -> str:
    """
    Phase 5: Translate deterministic API data into a patient-friendly summary.
    The LLM is only formatting known facts — it cannot add or infer drug information.
    """
    fact_block = (
        f"Drug Name: {drug_data.get('name', 'N/A')}\n"
        f"Labeler: {drug_data.get('labeler', 'N/A')}\n"
        f"Strength: {drug_data.get('strength', 'N/A')}\n"
        f"Dosage Form: {drug_data.get('dosageForm', 'N/A')}\n"
        f"Route: {drug_data.get('route', 'N/A')}\n"
        f"Source: {drug_data.get('source', 'NIH RxImage')}\n"
    )

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SYNTHESIS_PROMPT},
            {"role": "user", "content": fact_block}
        ],
        max_tokens=300,
        temperature=0.2
    )

    return response.choices[0].message.content.strip()
