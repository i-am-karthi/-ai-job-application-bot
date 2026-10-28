import os
import httpx

async def search_public_jobs(query: str, location: str = "Bengaluru", count: int = 10):
    """
    Uses Brave Search API when BRAVE_SEARCH_API_KEY is configured.
    Results are leads only; they must be verified on the employer's official careers page.
    """
    key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not key:
        raise RuntimeError("Set BRAVE_SEARCH_API_KEY in .env to enable web job discovery.")
    q = f'{query} jobs {location} site:careers OR site:jobs'
    async with httpx.AsyncClient(timeout=25) as client:
        resp = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": q, "count": min(max(count, 1), 20)},
            headers={"Accept": "application/json", "X-Subscription-Token": key}
        )
        resp.raise_for_status()
        payload = resp.json()
    results = []
    for item in payload.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
            "source": item.get("profile", {}).get("long_name", ""),
            "verification_status": "unverified_lead"
        })
    return {"query": q, "results": results,
            "notice": "Search results are unverified leads. Open the employer's official career page and confirm the role is active before adding it."}
