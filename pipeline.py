"""Run all available scrapers, validate their data and aggregate into a CSV.

This script loads the unified JSON schema from ``schema.json`` and uses it
to validate each record returned by the scrapers.  Valid records are written
to ``combined_projects.csv`` in the project root.  Invalid records trigger
warnings but do not stop the pipeline.
"""

from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import List

import pandas as pd
from jsonschema import validate, ValidationError

from scrapers.base import ProjectScraper


logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# List of scraper module names to run
SCRAPER_MODULES = [
    "scrapers.eureka",
    "scrapers.richmond",
]


def load_schema() -> dict:
    schema_path = Path(__file__).resolve().parent / "schema.json"
    with open(schema_path, "r") as f:
        return json.load(f)


def run_scrapers() -> List[dict]:
    records: List[dict] = []
    for module_name in SCRAPER_MODULES:
        try:
            module = importlib.import_module(module_name)
            # Find the scraper class (assumes only one class inheriting from ProjectScraper)
            scraper_cls = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, ProjectScraper) and attr is not ProjectScraper:
                    scraper_cls = attr
                    break
            if not scraper_cls:
                logger.warning("No scraper class found in %s", module_name)
                continue
            scraper = scraper_cls()
            logger.info("Running scraper: %s", scraper_cls.__name__)
            scraped = scraper.scrape()
            logger.info("  %d records scraped", len(scraped))
            records.extend(scraped)
        except Exception as e:
            logger.error("Error running scraper %s: %s", module_name, e)
    return records


def validate_records(records: List[dict], schema: dict) -> List[dict]:
    valid_records = []
    for rec in records:
        try:
            validate(instance=rec, schema=schema)
            valid_records.append(rec)
        except ValidationError as ve:
            logger.warning("Record failed validation: %s", ve.message)
    return valid_records


def main() -> None:
    schema = load_schema()
    records = run_scrapers()
    logger.info("Total records scraped: %d", len(records))
    valid_records = validate_records(records, schema)
    logger.info("Valid records: %d", len(valid_records))
    if valid_records:
        df = pd.DataFrame(valid_records)
        output_path = Path(__file__).resolve().parent / "combined_projects.csv"
        df.to_csv(output_path, index=False)
        logger.info("Data written to %s", output_path)
    else:
        logger.warning("No valid records to write")


if __name__ == "__main__":
    main()