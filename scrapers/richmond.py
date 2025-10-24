"""Scraper for City of Richmond major projects.

The City of Richmond publishes a list of major projects on its official website.
The page layout may consist of sections or cards rather than a single table,
so this scraper searches for headings and associated descriptions.  Parsed
records are mapped into the unified schema.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
import logging
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .base import ProjectScraper


logger = logging.getLogger(__name__)


class RichmondScraper(ProjectScraper):
    source_url: str = "https://www.ci.richmond.ca.us/1404/Major-Projects"

    def _scrape(self) -> List[Dict[str, Optional[str]]]:
        records: List[Dict[str, Optional[str]]] = []
        try:
            resp = requests.get(self.source_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
            resp.raise_for_status()
        except Exception as e:
            logger.warning("Failed to fetch %s: %s", self.source_url, e)
            return records

        soup = BeautifulSoup(resp.text, "html.parser")
        # Look for project sections; on the Richmond site projects are listed in
        # <div class="project"> containers with headings and paragraphs.
        project_containers = soup.find_all("div", class_=lambda cls: cls and "project" in cls)
        if not project_containers:
            # Fallback: look for headings (h2 or h3) within the content area
            content = soup.find("div", id="ContentArea")
            project_containers = content.find_all(["h2", "h3"]) if content else []

        for container in project_containers:
            # Extract title
            if container.name in ["h2", "h3"]:
                title = container.get_text(strip=True)
                desc_el = container.find_next_sibling("p")
                description = desc_el.get_text(strip=True) if desc_el else ""
            else:
                title_el = container.find(["h2", "h3"])
                title = title_el.get_text(strip=True) if title_el else "Unknown Project"
                description = container.get_text(strip=True)

            if not title:
                continue
            # Generate ID
            hash_id = hashlib.sha256(title.encode("utf-8")).hexdigest()[:8]
            original_id = f"richmond-{hash_id}"
            record = self.build_record(
                original_id=original_id,
                title=title,
                description=description,
                status="planned",
                date=datetime.now().strftime("%Y-%m-%d"),
                url=self.source_url,
                buyer="City of Richmond",
                sector="Transportation",
                subsector="Roads",
            )
            records.append(record)
        return records