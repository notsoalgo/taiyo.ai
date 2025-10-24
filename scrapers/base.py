"""Base classes and utilities for project scrapers.

Each scraper should inherit from :class:`ProjectScraper` and implement
the :meth:`scrape` method to return a list of dictionaries conforming
to the unified data schema defined in ``../schema.json``.

Scrapers must fill in the required fields: original_id, aug_id, country_* fields,
region_* fields, title, status, date and url.  Optional procurement fields can be
left as ``None``.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional


class ProjectScraper:
    """Base class for all project scrapers.

    Subclasses should set ``source_url`` and implement the ``_scrape`` method.
    """

    # Constants for US sources
    country_name: str = "United States"
    country_code: str = "USA"
    region_name: str = "North America"
    region_code: str = "NAC"

    def __init__(self) -> None:
        if not hasattr(self, 'source_url'):
            raise ValueError("Scraper must define a source_url attribute")

    def generate_aug_id(self) -> str:
        """Generate a new UUID for a record."""
        return str(uuid.uuid4())

    def parse_date(self, date_str: str, fmt: str) -> str:
        """Parse a date string and return it in YYYY-MM-DD format."""
        dt = datetime.strptime(date_str, fmt)
        return dt.strftime("%Y-%m-%d")

    def scrape(self) -> List[Dict[str, Optional[str]]]:
        """Return a list of projects scraped from the source.

        Subclasses should override ``_scrape`` and assemble records using
        :meth:`build_record`.
        """
        return self._scrape()

    def build_record(
        self,
        *,
        original_id: str,
        title: str,
        description: str,
        status: str,
        date: str,
        url: str,
        procurementMethod: Optional[str] = None,
        budget: Optional[float] = None,
        currency: Optional[str] = None,
        buyer: Optional[str] = None,
        sector: Optional[str] = None,
        subsector: Optional[str] = None,
        map_coordinates: Optional[Dict] = None,
    ) -> Dict[str, Optional[str]]:
        """Assemble a record dictionary with all schema fields filled in.
        Additional optional fields can be provided; unspecified optional fields
        default to ``None``.
        """
        return {
            "original_id": original_id,
            "aug_id": self.generate_aug_id(),
            "country_name": self.country_name,
            "country_code": self.country_code,
            "region_name": self.region_name,
            "region_code": self.region_code,
            "title": title,
            "description": description,
            "status": status.lower(),
            "date": date,
            "procurementMethod": procurementMethod,
            "budget": budget,
            "currency": currency,
            "buyer": buyer,
            "sector": sector,
            "subsector": subsector,
            "map_coordinates": map_coordinates,
            "url": url,
        }

    def _scrape(self) -> List[Dict[str, Optional[str]]]:
        raise NotImplementedError