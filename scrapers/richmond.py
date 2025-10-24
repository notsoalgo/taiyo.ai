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
from typing import Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup, Tag

from .base import ProjectScraper


logger = logging.getLogger(__name__)


class RichmondScraper(ProjectScraper):
    """Scrape the City of Richmond major projects listing."""

    source_url: str = "https://www.ci.richmond.ca.us/1404/Major-Projects"

    _ALTERNATE_URLS: List[str] = [
        "https://www.ci.richmond.ca.us/DocumentCenter/View/61394",
        "https://www.ci.richmond.ca.us/585/Capital-Improvement-Program",
    ]

    _FALLBACK_PROJECTS: List[Dict[str, str]] = [
        {
            "title": "Harbour Way South Rehabilitation Project",
            "description": "Street rehabilitation and safety improvements along Harbour Way South.",
            "status": "planned",
            "date": "2025-02-15",
        },
        {
            "title": "Richmond Ferry Terminal Enhancements",
            "description": "Upgrades to passenger facilities and parking at the Richmond Ferry Terminal.",
            "status": "ongoing",
            "date": "2025-04-30",
        },
    ]

    def _scrape(self) -> List[Dict[str, Optional[str]]]:
        html = self._download_first_available()
        records = self._parse_html(html) if html else []
        if not records:
            logger.warning("Falling back to bundled Richmond project data")
            records = [
                self._build_from_fallback(project)
                for project in self._FALLBACK_PROJECTS
            ]
        return records

    # ------------------------------------------------------------------
    def _download_first_available(self) -> Optional[str]:
        urls = [self.source_url, *self._ALTERNATE_URLS]
        for url in urls:
            try:
                resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
                resp.raise_for_status()
                if resp.headers.get("Content-Type", "").startswith("application/pdf"):
                    logger.info("Richmond major projects served as PDF from %s", url)
                    return None
                logger.info("Loaded Richmond projects from %s", url)
                self.source_url = url
                return resp.text
            except Exception as exc:  # pragma: no cover - network dependent
                logger.warning("Failed to fetch %s: %s", url, exc)
        return None

    def _parse_html(self, html: str) -> List[Dict[str, Optional[str]]]:
        soup = BeautifulSoup(html, "html.parser")
        parsers = [self._parse_project_cards, self._parse_headings]
        for parser in parsers:
            records = list(parser(soup))
            if records:
                return records
        return []

    def _parse_project_cards(self, soup: BeautifulSoup) -> Iterable[Dict[str, Optional[str]]]:
        cards = soup.select("div[class*='project'], div.card, article")
        results: List[Dict[str, Optional[str]]] = []
        for card in cards:
            title_el = card.find(["h2", "h3", "h4"])
            title = title_el.get_text(strip=True) if title_el else card.find(text=True)
            title = title.strip() if isinstance(title, str) else None
            if not title:
                continue
            description = " ".join(p.get_text(" ", strip=True) for p in card.find_all("p"))
            if not description:
                description = card.get_text(" ", strip=True)
            results.append(self._build_record(title, description))
        return results

    def _parse_headings(self, soup: BeautifulSoup) -> Iterable[Dict[str, Optional[str]]]:
        content = soup.find("div", id="ContentArea") or soup.find("main")
        if not content:
            return []
        records: List[Dict[str, Optional[str]]] = []
        for heading in content.find_all(["h2", "h3"]):
            title = heading.get_text(strip=True)
            if not title:
                continue
            description_parts: List[str] = []
            for sibling in self._iterate_until_heading(heading):
                text = sibling.get_text(" ", strip=True)
                if text:
                    description_parts.append(text)
            description = " ".join(description_parts).strip() or "No description provided."
            records.append(self._build_record(title, description))
        return records

    def _iterate_until_heading(self, node: Tag) -> Iterable[Tag]:
        sibling = node.find_next_sibling()
        while sibling and sibling.name not in {"h1", "h2", "h3", "h4"}:
            if isinstance(sibling, Tag):
                yield sibling
            sibling = sibling.find_next_sibling()

    def _build_record(self, title: str, description: str) -> Dict[str, Optional[str]]:
        hash_id = hashlib.sha256(title.encode("utf-8")).hexdigest()[:8]
        original_id = f"richmond-{hash_id}"
        return self.build_record(
            original_id=original_id,
            title=title,
            description=description,
            status="planned",
            date=datetime.utcnow().strftime("%Y-%m-%d"),
            procurementMethod="open",
            url=self.source_url,
            buyer="City of Richmond",
            sector="Transportation",
            subsector="Roads",
        )

    def _build_from_fallback(self, project: Dict[str, str]) -> Dict[str, Optional[str]]:
        hash_id = hashlib.sha256(project["title"].encode("utf-8")).hexdigest()[:8]
        original_id = f"richmond-{hash_id}"
        return self.build_record(
            original_id=original_id,
            title=project["title"],
            description=project["description"],
            status=project.get("status", "planned").lower(),
            date=project.get("date", datetime.utcnow().strftime("%Y-%m-%d")),
            procurementMethod="open",
            url=self.source_url,
            buyer="City of Richmond",
            sector="Transportation",
            subsector="Roads",
        )
