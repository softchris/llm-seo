from __future__ import annotations

import httpx

DEFAULT_TIMEOUT = 15.0
USER_AGENT = "LLM-SEO-Analyzer/0.1 (site audit tool)"


async def fetch_page(url: str) -> dict:
    """Fetch the main page and supporting files (robots.txt, sitemap.xml, llms.txt)."""
    headers = {"User-Agent": USER_AGENT}
    result: dict = {}

    async with httpx.AsyncClient(
        headers=headers,
        timeout=DEFAULT_TIMEOUT,
        follow_redirects=True,
        verify=False,
    ) as client:
        # Main page
        try:
            resp = await client.get(url)
            result["page"] = {
                "status": resp.status_code,
                "html": resp.text,
                "headers": dict(resp.headers),
                "url": str(resp.url),
            }
        except Exception as exc:
            result["page"] = {"status": 0, "html": "", "headers": {}, "error": str(exc)}

        # Derive base URL
        from urllib.parse import urlparse

        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        # Supporting files
        for path, key in [
            ("/robots.txt", "robots"),
            ("/sitemap.xml", "sitemap"),
            ("/llms.txt", "llms_txt"),
        ]:
            try:
                r = await client.get(base + path)
                result[key] = {
                    "status": r.status_code,
                    "text": r.text if r.status_code == 200 else "",
                }
            except Exception:
                result[key] = {"status": 0, "text": ""}

    return result
