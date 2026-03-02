# TrustMRR Startups Dataset

This repository includes scraper tooling for TrustMRR startup data.

## Important coverage note

- The committed snapshot files (`trustmrr_startups.json` and `trustmrr_startups_dataset.tsv`) are a **homepage-linked sample** (69 startups).
- For full coverage, use the scraper in `sitemap` mode (default), which discovers startup URLs from TrustMRR sitemaps.

## Files

- `trustmrr_startups.json`: detailed sample export (homepage-linked startups).
- `trustmrr_startups_dataset.tsv`: tab-separated sample export.
- `scrape_trustmrr_startups.py`: Playwright scraper.
- `trustmrr_coverage_report.md`: measured startup/category counts from sitemap.

## Scraper output schema (TSV)

- `url`
- `slug`
- `name`
- `description`
- `all_time_revenue`
- `mrr_estimated`
- `rank`
- `active_subscriptions`
- `founder`
- `x_followers`
- `founded`
- `country`

## Re-scrape

```bash
pip install playwright
playwright install chromium

# Full-site (all sitemap startup URLs)
python scrape_trustmrr_startups.py --source sitemap --output trustmrr_startups_full.tsv

# Homepage-only subset (faster)
python scrape_trustmrr_startups.py --source homepage --output trustmrr_startups_homepage.tsv
```
