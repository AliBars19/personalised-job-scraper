"""Tests for the relevance filter."""

import pytest
from scraper.processors.relevance_filter import is_relevant_job


class TestStrongMatches:
    def test_restaurant_manager(self):
        assert is_relevant_job("Restaurant Manager", "Some Company") is True

    def test_hotel_general_manager(self):
        assert is_relevant_job("Hotel General Manager", "TipTopJob") is True

    def test_head_sommelier(self):
        assert is_relevant_job("Head Sommelier", "Oswald's") is True

    def test_sommelier(self):
        assert is_relevant_job("Sommelier", "Spring Restaurant") is True

    def test_wine_buyer(self):
        assert is_relevant_job("Senior Wine Buyer", "C&C Group") is True

    def test_front_of_house(self):
        assert is_relevant_job("Front of House Manager", "The Ivy") is True

    def test_food_and_beverage(self):
        assert is_relevant_job("Food & Beverage Manager", "Marriott") is True

    def test_bar_manager(self):
        assert is_relevant_job("Bar Manager", "Hilton") is True

    def test_concierge(self):
        assert is_relevant_job("Head Concierge", "The Savoy") is True

    def test_breakfast_manager(self):
        assert is_relevant_job("Breakfast Manager", "Imperial London Hotels") is True

    def test_guest_relations(self):
        assert is_relevant_job("Guest Relations Manager", "Hilton") is True

    def test_cellar_manager(self):
        assert is_relevant_job("Cellar Manager", "Berry Bros") is True

    def test_mixologist(self):
        assert is_relevant_job("Head Mixologist", "Soho House") is True


class TestGenericManagersWithHospitalityCompany:
    def test_gm_at_hotel(self):
        assert is_relevant_job("General Manager", "Hilton") is True

    def test_assistant_manager_at_restaurant(self):
        assert is_relevant_job("Assistant Manager", "Wagamama") is True

    def test_duty_manager_at_pub(self):
        assert is_relevant_job("Duty Manager", "Young's Pubs") is True

    def test_gm_at_wine_company(self):
        assert is_relevant_job("General Manager", "Majestic Wine") is True

    def test_operations_manager_at_hotel_group(self):
        assert is_relevant_job("Operations Manager", "Marriott International") is True


class TestGenericManagersAtNonHospitality:
    def test_gm_at_tech(self):
        assert is_relevant_job("General Manager", "Google") is False

    def test_team_manager_at_retail(self):
        assert is_relevant_job("Team Manager", "Burberry") is False

    def test_assistant_manager_at_bank(self):
        assert is_relevant_job("Assistant Manager", "HSBC") is False

    def test_duty_manager_at_random(self):
        assert is_relevant_job("Duty Manager", "SQS") is False


class TestJunkTitles:
    def test_software_engineer(self):
        assert is_relevant_job("Software Engineer", "Hilton") is False

    def test_quantity_surveyor(self):
        assert is_relevant_job("Quantity Surveyor", "DAMICOR") is False

    def test_personal_assistant(self):
        assert is_relevant_job("Personal Assistant", "HSBC") is False

    def test_nurse(self):
        assert is_relevant_job("Nurse Manager", "NHS") is False

    def test_care_worker(self):
        assert is_relevant_job("Care Worker", "Creative Support") is False

    def test_warehouse(self):
        assert is_relevant_job("Warehouse Manager", "Amazon") is False

    def test_construction(self):
        assert is_relevant_job("Construction Manager", "Balfour Beatty") is False

    def test_hr_manager(self):
        assert is_relevant_job("HR Manager", "Deloitte") is False


class TestEdgeCases:
    def test_empty_title(self):
        assert is_relevant_job("", "Hilton") is False

    def test_wine_bar_server(self):
        assert is_relevant_job("Wine Bar Server", "Blackbook Winery") is True

    def test_pub_with_space(self):
        assert is_relevant_job("Pub Manager", "Greene King") is True
