import httpx

RXIMAGE_URL = "https://rximage.nlm.nih.gov/api/rximage/1/rxbase"
OPENFDA_URL = "https://api.fda.gov/drug/ndc.json"


async def lookup_drug(color: str, shape: str, imprint: str) -> dict | None:
    """
    Phase 4: Deterministic lookup against NIH RxImage API.
    No AI inference is used here — ground truth only.
    """
    params = {
        "color": color,
        "shape": shape,
        "imprint": imprint,
        "imageSize": "original"
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(RXIMAGE_URL, params=params)

    if response.status_code != 200:
        return None

    data = response.json()
    results = data.get("replyList", [])

    if not results:
        return None

    # Return the top match
    top = results[0]
    return {
        "name": top.get("name"),
        "ndc11": top.get("ndc11"),
        "labeler": top.get("labeler"),
        "strength": top.get("strength"),
        "dosageForm": top.get("dosageForm"),
        "route": top.get("route"),
        "imageUrl": top.get("imageUrl"),
        "rxcui": top.get("rxcui"),
        "source": "NIH RxImage"
    }
