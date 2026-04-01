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


class TestBlacklistedCompanies:
    def test_sony_gm(self):
        assert is_relevant_job("General Manager", "Sony Interactive Entertainment") is False

    def test_dhl_gm(self):
        assert is_relevant_job("General Manager - London Aviation", "DHL Supply Chain") is False

    def test_hugo_boss_gm(self):
        assert is_relevant_job("General Manager (John Lewis UK)", "HUGO BOSS") is False

    def test_burberry_team_manager(self):
        assert is_relevant_job("Burberry Team Manager - Regent Street", "BoF Careers") is False

    def test_nfl_events(self):
        assert is_relevant_job("Retail Events Manager (NFL)", "GamblingCareers.com") is False

    def test_powerleague_club_manager(self):
        assert is_relevant_job("GENERAL/CLUB MANAGER", "Powerleague") is False

    def test_homes_for_students(self):
        assert is_relevant_job("General Manager - Student Accommodation", "Homes for Students") is False

    def test_hims_and_hers(self):
        assert is_relevant_job("General Manager, UK", "hims & hers") is False

    def test_too_good_to_go(self):
        assert is_relevant_job("Key Account Manager - Hospitality", "Too Good To Go") is False


class TestBlacklistedTitles:
    def test_audit_assistant(self):
        assert is_relevant_job("Audit Assistant Manager", "McGinnis Loy Associates") is False

    def test_tax_assistant(self):
        assert is_relevant_job("Corporate Tax Assistant Manager", "Pro-Tax Recruitment") is False

    def test_veterinary_receptionist(self):
        assert is_relevant_job("Veterinary Receptionist", "DNA Vetcare") is False

    def test_showroom_manager(self):
        assert is_relevant_job("General Showroom Manager in waiting", "Wren Kitchens") is False

    def test_property_manager(self):
        assert is_relevant_job("Property Manager", "LAH Property Marketing") is False

    def test_retail_trainee(self):
        assert is_relevant_job("Retail Trainee Manager - Surrey", "Majestic Wine") is False

    def test_logistics_manager(self):
        assert is_relevant_job("Logistics Manager", "DHL Supply Chain") is False

    def test_insurance_broker(self):
        assert is_relevant_job("Insurance Broker Manager", "AXA") is False


class TestWineSpecific:
    def test_wine_director(self):
        assert is_relevant_job("Director of Wine", "Cambridge House") is True

    def test_wine_trader(self):
        assert is_relevant_job("Senior Wine Trader", "Fluid Fusion") is True

    def test_wine_consultant(self):
        assert is_relevant_job("Wine Consultant", "Berry Bros") is True

    def test_wine_buyer(self):
        assert is_relevant_job("Fine Wine Buying Assistant", "targetjobs UK") is True

    def test_wine_specialist(self):
        assert is_relevant_job("Wine Specialist", "Jeroboams") is True

    def test_beverage_manager(self):
        assert is_relevant_job("Beverage Programme Assistant Manager", "The Birley Clubs") is True


class TestEdgeCases:
    def test_empty_title(self):
        assert is_relevant_job("", "Hilton") is False

    def test_wine_bar_server(self):
        assert is_relevant_job("Wine Bar Server", "Blackbook Winery") is True

    def test_pub_with_space(self):
        assert is_relevant_job("Pub Manager", "Greene King") is True

    def test_receptionist_at_hotel(self):
        # Plain "Receptionist" is too generic — we want hotel reception manager roles
        assert is_relevant_job("Receptionist", "Rosewood London") is False

    def test_hotel_receptionist(self):
        assert is_relevant_job("Hotel Receptionist", "Clermont Hotel Group") is True

    def test_reception_manager_at_hotel(self):
        assert is_relevant_job("Reception Manager", "Hilton") is True

    def test_receptionist_at_office(self):
        assert is_relevant_job("Receptionist", "Morgan Spencer") is False

    def test_receptionist_at_recruitment(self):
        assert is_relevant_job("Corporate Receptionist & Office Coordinator", "Morgan McKinley") is False

    def test_gm_at_known_restaurant(self):
        assert is_relevant_job("General Manager", "Duck & Waffle") is True

    def test_gm_at_known_pub_group(self):
        assert is_relevant_job("General Manager", "Urban Pubs and Bars") is True
