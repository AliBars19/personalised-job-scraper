"""Tests for the London location filter."""

import pytest
from scraper.processors.location_filter import is_london_based


class TestIsLondonBased:
    def test_explicit_london(self):
        assert is_london_based("London") is True

    def test_london_area(self):
        assert is_london_based("Central London") is True

    def test_london_with_district(self):
        assert is_london_based("London, W1") is True

    def test_ec_postcode(self):
        assert is_london_based("EC1A 1BB") is True

    def test_wc_postcode(self):
        assert is_london_based("WC2H 9JQ") is True

    def test_sw_postcode(self):
        assert is_london_based("SW1A 1AA") is True

    def test_se_postcode(self):
        assert is_london_based("SE1 7PB") is True

    def test_nw_postcode(self):
        assert is_london_based("NW1 4SA") is True

    def test_e_postcode(self):
        assert is_london_based("E14 5AB") is True

    def test_n_postcode(self):
        assert is_london_based("N1 9GU") is True

    def test_w_postcode(self):
        assert is_london_based("W1D 3AF") is True

    def test_non_london_city(self):
        assert is_london_based("Manchester") is False

    def test_non_london_postcode(self):
        assert is_london_based("M1 1AA") is False

    def test_empty_string(self):
        assert is_london_based("") is False

    def test_none_like_empty(self):
        assert is_london_based("") is False

    def test_case_insensitive(self):
        assert is_london_based("london") is True
        assert is_london_based("LONDON") is True
