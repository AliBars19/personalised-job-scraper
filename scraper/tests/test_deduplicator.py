"""Tests for the deduplication logic."""

import sys
from unittest.mock import MagicMock

# Mock supabase before importing deduplicator (it depends on supabase_client)
sys.modules["supabase"] = MagicMock()

import pytest
from scraper.processors.deduplicator import _normalise, _pick_canonical, deduplicate_job


class TestNormalise:
    def test_lowercase(self):
        assert _normalise("Restaurant Manager") == "restaurant manager"

    def test_strip_ltd(self):
        assert _normalise("Hilton Hotels Ltd") == "hilton hotels"

    def test_strip_limited(self):
        assert _normalise("The Ivy Collection Limited") == "the ivy collection"

    def test_strip_punctuation(self):
        assert _normalise("Corbin & King") == "corbin king"

    def test_strip_multiple_suffixes(self):
        assert _normalise("Premier Inn Holdings PLC") == "premier inn"


class TestPickCanonical:
    def test_longer_description_wins(self):
        a = {"id": "a", "description": "short", "salary_text": None}
        b = {"id": "b", "description": "this is a much longer description", "salary_text": None}
        canonical, dup = _pick_canonical(a, b)
        assert canonical == "b"
        assert dup == "a"

    def test_salary_text_wins(self):
        a = {"id": "a", "description": "desc", "salary_text": "£40k"}
        b = {"id": "b", "description": "description text here", "salary_text": None}
        canonical, dup = _pick_canonical(a, b)
        assert canonical == "a"
        assert dup == "b"


class TestDeduplicateJob:
    def test_detects_duplicate(self):
        db = MagicMock()
        job = {
            "id": "new-id",
            "title": "Restaurant General Manager",
            "company": "The Ivy Collection",
            "location": "London",
        }
        existing = [
            {
                "id": "existing-id",
                "title": "Restaurant General Manager",
                "company": "The Ivy Collection Ltd",
                "location": "London, W1",
                "description": "Full description here",
                "salary_text": "£45k",
            }
        ]

        result = deduplicate_job(job, existing, db)
        assert result is True
        db.mark_duplicate.assert_called_once()

    def test_no_duplicate_different_title(self):
        db = MagicMock()
        job = {
            "id": "new-id",
            "title": "Head Sommelier",
            "company": "The Ivy Collection",
            "location": "London",
        }
        existing = [
            {
                "id": "existing-id",
                "title": "Restaurant General Manager",
                "company": "The Ivy Collection",
                "location": "London",
                "description": "",
                "salary_text": None,
            }
        ]

        result = deduplicate_job(job, existing, db)
        assert result is False
        db.mark_duplicate.assert_not_called()

    def test_no_duplicate_different_company(self):
        db = MagicMock()
        job = {
            "id": "new-id",
            "title": "Restaurant Manager",
            "company": "Corbin & King",
            "location": "London",
        }
        existing = [
            {
                "id": "existing-id",
                "title": "Restaurant Manager",
                "company": "Hilton Hotels",
                "location": "London",
                "description": "",
                "salary_text": None,
            }
        ]

        result = deduplicate_job(job, existing, db)
        assert result is False
