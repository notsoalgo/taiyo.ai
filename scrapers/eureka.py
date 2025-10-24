"""Scraper for the City of Eureka upcoming projects.

This scraper downloads the "Upcoming Projects" page from the City of Eureka
website, extracts rows from the projects table and maps them into the unified
schema.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .base import ProjectScraper


logger = logging.getLogger(__name__)


class EurekaScraper(ProjectScraper):
    source_url: str = "https://www.eurekaca.gov/744/Upcoming-Projects"

    def _scrape(self) -> List[Dict[str, Optional[str]]]:
        records: List[Dict[str, Optional[str]]] = []
        try:
            resp = requests.get(self.source_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", self.source_url, e)
            return records

        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find("table")
        if not table:
            logger.warning("Could not find a table on %s", self.source_url)
            return records

        rows = table.find_all("tr")[1:]
        for row in rows:
            cols = [c.get_text(strip=True) for c in row.find_all(["td", "th"])]
            # Make sure there are at least four columns; adjust indexing as needed.
            if len(cols) < 4:
                continue
            title, status, description, date_str = cols[0], cols[1], cols[2], cols[3]
            # Derive original_id from title hash
            hash_id = hashlib.sha256(title.encode("utf-8")).hexdigest()[:8]
            original_id = f"eureka-{hash_id}"
            # Try to parse date; fallback to provided string if parsing fails
            try:
                date = self.parse_date(date_str, "%B %d, %Y")
            except Exception:
                date = date_str
            record = self.build_record(
                original_id=original_id,
                title=title,
                description=description,
                status=status,
                date=date,
                url=self.source_url,
                buyer="City of Eureka",
                sector="Transportation",
                subsector="Roads",
            )
            records.append(record)
        return records