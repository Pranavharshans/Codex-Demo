#!/usr/bin/env python3
"""Scrape startup data from TrustMRR.

Default mode discovers startup URLs from sitemap(s), which is broader than homepage-only links.
"""
import argparse
import asyncio
import csv
from typing import Iterable, List, Dict
from urllib.parse import urljoin
import xml.etree.ElementTree as ET

from playwright.async_api import async_playwright

BASE_URL = "https://trustmrr.com"
SITEMAP_INDEX = f"{BASE_URL}/sitemap.xml"

COLUMNS = [
    "url",
    "slug",
    "name",
    "description",
    "all_time_revenue",
    "mrr_estimated",
    "rank",
    "active_subscriptions",
    "founder",
    "x_followers",
    "founded",
    "country",
]


def extract_after(lines: List[str], label: str) -> str:
    if label in lines:
        i = lines.index(label)
        if i + 1 < len(lines):
            return lines[i + 1]
    return ""


def parse_xml_locs(xml_text: str) -> List[str]:
    root = ET.fromstring(xml_text)
    return [el.text.strip() for el in root.iter() if el.tag.endswith("loc") and el.text]


async def fetch_text(page, url: str) -> str:
    response = await page.goto(url, wait_until="domcontentloaded")
    if not response or response.status >= 400:
        raise RuntimeError(f"Failed to fetch {url}: HTTP {response.status if response else 'N/A'}")
    return await page.text_content("body") or ""


async def discover_startup_urls_from_sitemaps(page) -> List[str]:
    index_text = await fetch_text(page, SITEMAP_INDEX)
    sitemap_urls = parse_xml_locs(index_text)

    startup_urls = set()
    for sitemap_url in sitemap_urls:
        xml_text = await fetch_text(page, sitemap_url)
        for loc in parse_xml_locs(xml_text):
            if "/startup/" in loc:
                startup_urls.add(loc)
    return sorted(startup_urls)


async def discover_startup_urls_from_homepage(page) -> List[str]:
    await page.goto(BASE_URL, wait_until="networkidle")
    slugs = await page.eval_on_selector_all(
        'a[href^="/startup/"]',
        'els => Array.from(new Set(els.map(e => e.getAttribute("href"))))',
    )
    return sorted(urljoin(BASE_URL, slug) for slug in slugs)


async def extract_startup(detail_page, url: str) -> Dict[str, str]:
    await detail_page.goto(url, wait_until="domcontentloaded")
    body = await detail_page.inner_text("body")
    lines = [x.strip() for x in body.split("\n") if x.strip()]

    title = await detail_page.title()
    desc = await detail_page.locator('meta[name="description"]').get_attribute("content") or ""

    rank = next((ln for ln in lines if "Ranked #" in ln and "TrustMRR" in ln), "")
    active_subscriptions = next((ln for ln in lines if "active subscriptions" in ln), "")
    x_followers = next((ln for ln in lines if "followers on 𝕏" in ln), "")

    country = ""
    if "Founded" in lines:
        idx = lines.index("Founded")
        if idx + 2 < len(lines):
            country = lines[idx + 2]

    return {
        "url": url,
        "slug": "/startup/" + url.rstrip("/").split("/startup/")[-1],
        "name": title.split(" - ")[0],
        "description": desc,
        "all_time_revenue": extract_after(lines, "All-time revenue"),
        "mrr_estimated": extract_after(lines, "MRR (estimated)"),
        "rank": rank,
        "active_subscriptions": active_subscriptions,
        "founder": extract_after(lines, "Founder"),
        "x_followers": x_followers,
        "founded": extract_after(lines, "Founded"),
        "country": country,
    }


async def scrape(output_path: str, source: str, limit: int = 0):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        if source == "homepage":
            startup_urls = await discover_startup_urls_from_homepage(page)
        else:
            startup_urls = await discover_startup_urls_from_sitemaps(page)

        if limit > 0:
            startup_urls = startup_urls[:limit]

        detail = await browser.new_page()
        rows = []
        for i, url in enumerate(startup_urls, start=1):
            try:
                row = await extract_startup(detail, url)
                rows.append(row)
            except Exception:
                continue
            if i % 100 == 0:
                print(f"Processed {i}/{len(startup_urls)}")

        await browser.close()

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="trustmrr_startups_dataset.tsv")
    parser.add_argument("--source", choices=["sitemap", "homepage"], default="sitemap")
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()
    asyncio.run(scrape(output_path=args.output, source=args.source, limit=args.limit))


if __name__ == "__main__":
    main()
