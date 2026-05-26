"""Individual LLM-readiness checks.

Each check function receives the fetched data dict and returns a CheckResult.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from bs4 import BeautifulSoup


@dataclass
class CheckResult:
    name: str
    score: int  # 0-10
    max_score: int = 10
    status: str = "fail"  # pass | partial | fail
    findings: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": self.score,
            "max_score": self.max_score,
            "status": self.status,
            "findings": self.findings,
            "actions": self.actions,
        }


AI_BOTS = [
    "GPTBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-Web",
    "Amazonbot",
    "anthropic-ai",
    "Google-Extended",
    "PerplexityBot",
    "Bytespider",
    "cohere-ai",
]


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# ── 1. robots.txt ──────────────────────────────────────────────────────

def check_robots(data: dict) -> CheckResult:
    r = data.get("robots", {})
    if r.get("status") != 200 or not r.get("text", "").strip():
        return CheckResult(
            name="robots.txt",
            score=0,
            findings=["No robots.txt found at site root."],
            actions=["Create a /robots.txt file that explicitly allows AI crawlers."],
        )

    text = r["text"].lower()
    blocked: list[str] = []
    allowed: list[str] = []

    for bot in AI_BOTS:
        bot_lower = bot.lower()
        # Look for user-agent blocks that disallow the bot
        pattern = rf"user-agent:\s*{re.escape(bot_lower)}"
        if re.search(pattern, text):
            # Check if there's a Disallow: / for this bot
            section = text[text.index(bot_lower):]
            if "disallow: /" in section.split("user-agent:")[0]:
                blocked.append(bot)
            else:
                allowed.append(bot)

    # Check for blanket disallow
    blanket_block = False
    if "user-agent: *" in text:
        ua_star_section = text.split("user-agent: *")[1].split("user-agent:")[0] if "user-agent:" in text.split("user-agent: *")[1] else text.split("user-agent: *")[1]
        if "disallow: /" in ua_star_section:
            lines = ua_star_section.strip().split("\n")
            for line in lines:
                line = line.strip()
                if line == "disallow: /":
                    blanket_block = True
                    break

    findings = ["robots.txt exists."]
    actions = []
    score = 4  # base for having the file

    if blanket_block:
        findings.append("⚠ Blanket 'Disallow: /' found for all user-agents.")
        actions.append("Consider allowing AI crawlers by adding specific Allow rules or removing the blanket block.")
        score = 3
    else:
        score = 6

    if blocked:
        findings.append(f"Blocked AI bots: {', '.join(blocked)}")
        actions.append(f"Consider unblocking: {', '.join(blocked)}")
        score = max(score - len(blocked), 2)
    elif not blanket_block:
        findings.append("No AI bots are explicitly blocked.")
        score = 10

    status = "pass" if score >= 8 else "partial" if score >= 4 else "fail"
    return CheckResult(name="robots.txt", score=score, status=status, findings=findings, actions=actions)


# ── 2. llms.txt ────────────────────────────────────────────────────────

def check_llms_txt(data: dict) -> CheckResult:
    r = data.get("llms_txt", {})
    if r.get("status") != 200 or not r.get("text", "").strip():
        return CheckResult(
            name="llms.txt",
            score=0,
            findings=["No /llms.txt file found."],
            actions=[
                "Create a /llms.txt file describing your site's purpose, key pages, and API endpoints for LLM consumption.",
                "See https://llmstxt.org for the emerging specification.",
            ],
        )

    text = r["text"]
    lines = [l.strip() for l in text.strip().split("\n") if l.strip()]
    findings = [f"llms.txt found with {len(lines)} lines."]
    actions = []
    score = 7

    if len(lines) < 3:
        findings.append("File is very short — may lack useful content.")
        actions.append("Add more detail: site description, key URLs, API docs links.")
        score = 4
    else:
        score = 10

    status = "pass" if score >= 8 else "partial"
    return CheckResult(name="llms.txt", score=score, status=status, findings=findings, actions=actions)


# ── 3. Sitemap ─────────────────────────────────────────────────────────

def check_sitemap(data: dict) -> CheckResult:
    r = data.get("sitemap", {})
    if r.get("status") != 200 or not r.get("text", "").strip():
        return CheckResult(
            name="Sitemap",
            score=0,
            findings=["No /sitemap.xml found."],
            actions=["Create a sitemap.xml listing your key pages so AI agents can discover content."],
        )

    text = r["text"]
    url_count = text.lower().count("<url>") or text.lower().count("<loc>")
    findings = [f"sitemap.xml found with ~{url_count} URLs." if url_count else "sitemap.xml found (index or non-standard format)."]
    score = 8 if url_count > 0 else 5
    actions = []

    if url_count == 0:
        actions.append("Ensure sitemap contains <url><loc>...</loc></url> entries.")
    if url_count > 0 and url_count < 5:
        actions.append("Consider adding more pages to the sitemap for better discoverability.")
        score = 7

    if url_count >= 5:
        score = 10

    status = "pass" if score >= 8 else "partial"
    return CheckResult(name="Sitemap", score=score, status=status, findings=findings, actions=actions)


# ── 4. Structured Data ────────────────────────────────────────────────

def check_structured_data(data: dict) -> CheckResult:
    html = data.get("page", {}).get("html", "")
    soup = _soup(html)

    json_ld_scripts = soup.find_all("script", type="application/ld+json")
    microdata = soup.find_all(attrs={"itemscope": True})

    findings = []
    actions = []
    score = 0

    if json_ld_scripts:
        types_found = []
        for script in json_ld_scripts:
            try:
                obj = json.loads(script.string or "")
                if isinstance(obj, dict):
                    types_found.append(obj.get("@type", "Unknown"))
                elif isinstance(obj, list):
                    types_found.extend(item.get("@type", "Unknown") for item in obj if isinstance(item, dict))
            except (json.JSONDecodeError, TypeError):
                pass
        findings.append(f"Found {len(json_ld_scripts)} JSON-LD block(s): {', '.join(types_found) if types_found else 'unparseable'}.")
        score += 7

    if microdata:
        findings.append(f"Found {len(microdata)} microdata element(s).")
        score += 3

    if not json_ld_scripts and not microdata:
        findings.append("No structured data (JSON-LD or microdata) found.")
        actions.append("Add JSON-LD structured data (schema.org) — Organization, WebPage, Article, FAQPage, etc.")
        actions.append("This helps LLMs understand your content type and extract key facts.")

    score = min(score, 10)
    status = "pass" if score >= 7 else "partial" if score >= 3 else "fail"
    return CheckResult(name="Structured Data", score=score, status=status, findings=findings, actions=actions)


# ── 5. Semantic HTML ──────────────────────────────────────────────────

def check_semantic_html(data: dict) -> CheckResult:
    html = data.get("page", {}).get("html", "")
    soup = _soup(html)

    tags_to_check = {"main": 0, "nav": 0, "article": 0, "section": 0, "header": 0, "footer": 0, "aside": 0}
    for tag in tags_to_check:
        tags_to_check[tag] = len(soup.find_all(tag))

    found = {k: v for k, v in tags_to_check.items() if v > 0}
    missing = [k for k, v in tags_to_check.items() if v == 0]

    findings = []
    actions = []

    if found:
        findings.append(f"Semantic tags found: {', '.join(f'<{k}> ({v})' for k, v in found.items())}.")
    if missing:
        findings.append(f"Missing semantic tags: {', '.join(f'<{t}>' for t in missing)}.")

    # Score: proportional to how many semantic tags are used
    score = min(round(len(found) / len(tags_to_check) * 10), 10)

    if "main" not in found:
        actions.append("Add a <main> element to wrap your primary content — critical for LLM content extraction.")
    if "nav" not in found:
        actions.append("Add <nav> for navigation — helps agents understand site structure.")
    if "article" not in found and "section" not in found:
        actions.append("Use <article> or <section> to delineate content blocks.")

    status = "pass" if score >= 7 else "partial" if score >= 4 else "fail"
    return CheckResult(name="Semantic HTML", score=score, status=status, findings=findings, actions=actions)


# ── 6. Meta Description ──────────────────────────────────────────────

def check_meta_description(data: dict) -> CheckResult:
    html = data.get("page", {}).get("html", "")
    soup = _soup(html)

    meta = soup.find("meta", attrs={"name": "description"})
    title = soup.find("title")

    findings = []
    actions = []
    score = 0

    if title and title.string and title.string.strip():
        findings.append(f"Title tag: \"{title.string.strip()[:80]}\"")
        score += 4
    else:
        findings.append("No <title> tag found.")
        actions.append("Add a descriptive <title> tag.")

    if meta and meta.get("content", "").strip():
        content = meta["content"].strip()
        findings.append(f"Meta description ({len(content)} chars): \"{content[:100]}{'…' if len(content) > 100 else ''}\"")
        if len(content) < 50:
            actions.append("Meta description is too short. Aim for 120-160 characters.")
            score += 3
        elif len(content) > 300:
            actions.append("Meta description is too long. Keep it under 160 characters.")
            score += 4
        else:
            score += 6
    else:
        findings.append("No meta description found.")
        actions.append("Add <meta name='description' content='...'> with a concise page summary (120-160 chars).")

    status = "pass" if score >= 8 else "partial" if score >= 4 else "fail"
    return CheckResult(name="Meta Description", score=score, status=status, findings=findings, actions=actions)


# ── 7. Open Graph ─────────────────────────────────────────────────────

def check_open_graph(data: dict) -> CheckResult:
    html = data.get("page", {}).get("html", "")
    soup = _soup(html)

    og_tags = {}
    for meta in soup.find_all("meta", attrs={"property": re.compile(r"^og:")}):
        og_tags[meta["property"]] = meta.get("content", "")

    findings = []
    actions = []

    required = ["og:title", "og:description", "og:type", "og:url"]
    present = [t for t in required if t in og_tags]
    missing = [t for t in required if t not in og_tags]

    if present:
        for tag in present:
            findings.append(f"{tag}: \"{og_tags[tag][:80]}\"")

    score = round(len(present) / len(required) * 10)

    if missing:
        findings.append(f"Missing OG tags: {', '.join(missing)}")
        actions.append(f"Add the following Open Graph tags: {', '.join(missing)}")
        actions.append("OG tags help LLMs and agents understand page purpose when shared or indexed.")

    if "og:image" in og_tags:
        findings.append(f"og:image present: {og_tags['og:image'][:80]}")

    status = "pass" if score >= 8 else "partial" if score >= 5 else "fail"
    return CheckResult(name="Open Graph", score=score, status=status, findings=findings, actions=actions)


# ── 8. Content Clarity ────────────────────────────────────────────────

def check_content_clarity(data: dict) -> CheckResult:
    html = data.get("page", {}).get("html", "")
    soup = _soup(html)

    # Remove scripts and styles
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text_len = len(text)
    html_len = len(html) if html else 1

    ratio = text_len / html_len if html_len > 0 else 0

    findings = []
    actions = []

    findings.append(f"Text content: {text_len:,} chars, HTML size: {html_len:,} chars.")
    findings.append(f"Text-to-HTML ratio: {ratio:.1%}")

    # Count paragraphs with substantial text
    paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40]
    findings.append(f"Substantial paragraphs (>40 chars): {len(paragraphs)}")

    score = 0
    if ratio >= 0.25:
        score = 8
    elif ratio >= 0.15:
        score = 6
    elif ratio >= 0.08:
        score = 4
    else:
        score = 2
        actions.append("Very low text-to-HTML ratio — content may be generated by JavaScript or hidden in iframes.")

    if len(paragraphs) >= 3:
        score = min(score + 2, 10)
    elif len(paragraphs) == 0:
        actions.append("No substantial <p> elements found. Structure content in paragraphs for better LLM parsing.")

    if text_len < 200:
        actions.append("Page has very little text content. LLMs need readable text to understand your site.")
        score = max(score - 3, 0)

    status = "pass" if score >= 7 else "partial" if score >= 4 else "fail"
    return CheckResult(name="Content Clarity", score=score, status=status, findings=findings, actions=actions)


# ── 9. Heading Structure ─────────────────────────────────────────────

def check_headings(data: dict) -> CheckResult:
    html = data.get("page", {}).get("html", "")
    soup = _soup(html)

    headings: dict[str, list[str]] = {}
    for level in range(1, 7):
        tag = f"h{level}"
        headings[tag] = [h.get_text(strip=True)[:80] for h in soup.find_all(tag)]

    findings = []
    actions = []
    score = 0

    h1s = headings.get("h1", [])
    if len(h1s) == 1:
        findings.append(f"Single H1: \"{h1s[0]}\"")
        score += 5
    elif len(h1s) == 0:
        findings.append("No H1 tag found.")
        actions.append("Add a single <h1> that clearly describes the page content.")
    else:
        findings.append(f"Multiple H1 tags found ({len(h1s)}): {', '.join(h1s[:3])}")
        actions.append("Use only one <h1> per page for clear content hierarchy.")
        score += 2

    # Check for heading hierarchy
    total_headings = sum(len(v) for v in headings.values())
    if total_headings > 1:
        breakdown = ", ".join(f"{k}: {len(v)}" for k, v in headings.items() if v)
        findings.append(f"Heading breakdown: {breakdown}")
        score += 3

        # Check for skipped levels
        levels_used = [int(k[1]) for k, v in headings.items() if v]
        if levels_used:
            for i in range(len(levels_used) - 1):
                if levels_used[i + 1] - levels_used[i] > 1:
                    actions.append(f"Heading levels skip from H{levels_used[i]} to H{levels_used[i+1]}. Use sequential levels for logical structure.")
                    break
            else:
                score += 2
    else:
        findings.append("Very few headings found on the page.")
        actions.append("Add heading hierarchy (H1 → H2 → H3) to structure content for AI parsing.")

    score = min(score, 10)
    status = "pass" if score >= 7 else "partial" if score >= 4 else "fail"
    return CheckResult(name="Heading Structure", score=score, status=status, findings=findings, actions=actions)


# ── 10. Canonical & Language ──────────────────────────────────────────

def check_canonical_lang(data: dict) -> CheckResult:
    html = data.get("page", {}).get("html", "")
    soup = _soup(html)

    findings = []
    actions = []
    score = 0

    # Canonical URL
    canonical = soup.find("link", rel="canonical")
    if canonical and canonical.get("href"):
        findings.append(f"Canonical URL: {canonical['href'][:100]}")
        score += 5
    else:
        findings.append("No canonical URL set.")
        actions.append("Add <link rel='canonical' href='...'> to avoid duplicate content issues with LLM indexing.")

    # Language
    html_tag = soup.find("html")
    if html_tag and html_tag.get("lang"):
        findings.append(f"Language attribute: {html_tag['lang']}")
        score += 5
    else:
        findings.append("No lang attribute on <html> tag.")
        actions.append("Add lang='en' (or appropriate language) to the <html> tag so LLMs know the content language.")

    status = "pass" if score >= 8 else "partial" if score >= 5 else "fail"
    return CheckResult(name="Canonical & Language", score=score, status=status, findings=findings, actions=actions)
