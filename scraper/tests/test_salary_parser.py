"""Tests for the salary parser."""

import pytest
from scraper.processors.salary_parser import parse_salary


class TestParseSalary:
    def test_none_input(self):
        assert parse_salary(None) == (None, None)

    def test_empty_string(self):
        assert parse_salary("") == (None, None)

    def test_competitive(self):
        assert parse_salary("Competitive") == (None, None)

    def test_negotiable(self):
        assert parse_salary("Negotiable salary") == (None, None)

    def test_dependent_on_experience(self):
        assert parse_salary("Salary dependent on experience") == (None, None)

    def test_range_with_commas(self):
        result = parse_salary("£35,000 - £42,000")
        assert result == (3_500_000, 4_200_000)

    def test_range_with_k_suffix(self):
        result = parse_salary("£35k - £42k")
        assert result == (3_500_000, 4_200_000)

    def test_range_per_annum(self):
        result = parse_salary("£35,000 - £42,000 per annum")
        assert result == (3_500_000, 4_200_000)

    def test_hourly_rate(self):
        result = parse_salary("£18 - £22 per hour")
        min_val, max_val = result
        assert min_val == 18 * 2080 * 100  # £18/hr * 2080hrs * 100 pence
        assert max_val == 22 * 2080 * 100

    def test_up_to(self):
        result = parse_salary("Up to £50,000")
        assert result == (None, 5_000_000)

    def test_single_value(self):
        result = parse_salary("£40,000")
        assert result == (4_000_000, 4_000_000)

    def test_with_bonus(self):
        result = parse_salary("£40,000 + bonus")
        assert result == (4_000_000, 4_000_000)

    def test_doe(self):
        assert parse_salary("DOE") == (None, None)
