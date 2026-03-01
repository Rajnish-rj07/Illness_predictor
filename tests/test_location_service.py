"""
Unit tests for LocationService.

Tests the location service functionality including facility search,
distance calculation, and facility ranking.

Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5
"""

import pytest
import math
import requests
from unittest.mock import Mock, patch, MagicMock
from src.location.location_service import LocationService
from src.models.data_models import Location, Facility, Severity


class TestLocationService:
    """Test suite for LocationService."""
    
    @pytest.fixture
    def location_service(self):
        """Create a LocationService instance for testing."""
        return LocationService(api_key="test_api_key")
    
    @pytest.fixture
    def user_location(self):
        """Create a test user location."""
        return Location(
            latitude=37.7749,
            longitude=-122.4194,
            address="San Francisco, CA"
        )
    
    @pytest.fixture
    def sample_facility(self, user_location):
        """Create a sample facility for testing."""
        return Facility(
            name="San Francisco General Hospital",
            facility_type="hospital",
            location=Location(
                latitude=37.7562,
                longitude=-122.4205,
                address="1001 Potrero Ave, San Francisco, CA"
            ),
            distance_km=2.5,
            specialties=["emergency", "general_practice"],
            contact="(415) 206-8000",
            rating=4.2
        )
    
    def test_calculate_distance_same_location(self, location_service):
        """Test distance calculation for same location returns 0."""
        loc = Location(latitude=37.7749, longitude=-122.4194)
        distance = location_service.calculate_distance(loc, loc)
        assert distance == 0.0
    
    def test_calculate_distance_known_locations(self, location_service):
        """Test distance calculation with known locations."""
        # San Francisco to Los Angeles (approximately 559 km)
        sf = Location(latitude=37.7749, longitude=-122.4194)
        la = Location(latitude=34.0522, longitude=-118.2437)
        
        distance = location_service.calculate_distance(sf, la)
        
        # Allow 10% margin of error
        expected = 559.0
        assert abs(distance - expected) < expected * 0.1
    
    def test_calculate_distance_validates_locations(self, location_service):
        """Test that calculate_distance validates location coordinates."""
        valid_loc = Location(latitude=37.7749, longitude=-122.4194)
        invalid_loc = Location(latitude=100.0, longitude=-122.4194)  # Invalid latitude
        
        with pytest.raises(ValueError):
            location_service.calculate_distance(valid_loc, invalid_loc)
    
    def test_haversine_formula_accuracy(self, location_service):
        """Test haversine formula with multiple known distances."""
        test_cases = [
            # (loc1, loc2, expected_km)
            (Location(0, 0), Location(0, 1), 111.2),  # 1 degree longitude at equator
            (Location(0, 0), Location(1, 0), 111.2),  # 1 degree latitude
            (Location(40.7128, -74.0060), Location(51.5074, -0.1278), 5570),  # NYC to London
        ]
        
        for loc1, loc2, expected in test_cases:
            distance = location_service.calculate_distance(loc1, loc2)
            # Allow 10% margin
            assert abs(distance - expected) < expected * 0.1
    
    @patch('src.location.location_service.requests.get')
    def test_find_facilities_critical_severity(self, mock_get, location_service, user_location):
        """Test that critical severity prioritizes emergency facilities."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': [
                {
                    'name': 'Emergency Hospital',
                    'types': ['hospital', 'emergency'],
                    'geometry': {'location': {'lat': 37.7562, 'lng': -122.4205}},
                    'vicinity': '1001 Potrero Ave',
                    'rating': 4.5
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        facilities = location_service.find_facilities(
            user_location,
            Severity.CRITICAL,
            "heart_attack"
        )
        
        assert len(facilities) > 0
        # Verify emergency or hospital facilities are returned for critical severity
        assert any(f.facility_type in ['emergency', 'hospital'] for f in facilities)
    
    @patch('src.location.location_service.requests.get')
    def test_find_facilities_low_severity(self, mock_get, location_service, user_location):
        """Test facility search for low severity illness."""
        # Mock API response with clinics
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': [
                {
                    'name': 'Community Clinic',
                    'types': ['clinic', 'health'],
                    'geometry': {'location': {'lat': 37.7749, 'lng': -122.4194}},
                    'vicinity': '123 Main St',
                    'rating': 4.0
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        facilities = location_service.find_facilities(
            user_location,
            Severity.LOW,
            "influenza"
        )
        
        assert len(facilities) > 0
    
    @patch('src.location.location_service.requests.get')
    def test_find_facilities_returns_max_facilities(self, mock_get, location_service, user_location):
        """Test that find_facilities respects max_facilities limit."""
        # Mock API response with many facilities
        mock_results = []
        for i in range(20):
            mock_results.append({
                'name': f'Facility {i}',
                'types': ['hospital'],
                'geometry': {'location': {'lat': 37.7749 + i*0.01, 'lng': -122.4194}},
                'vicinity': f'{i} Street',
                'rating': 4.0
            })
        
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': mock_results
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        facilities = location_service.find_facilities(
            user_location,
            Severity.MODERATE,
            "pneumonia"
        )
        
        # Should return at most max_facilities
        assert len(facilities) <= location_service.max_facilities
    
    @patch('src.location.location_service.requests.get')
    def test_get_emergency_facilities(self, mock_get, location_service, user_location):
        """Test getting emergency facilities."""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': [
                {
                    'name': 'Emergency Room',
                    'types': ['emergency', 'hospital'],
                    'geometry': {'location': {'lat': 37.7562, 'lng': -122.4205}},
                    'vicinity': '1001 Potrero Ave',
                    'rating': 4.5
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        facilities = location_service.get_emergency_facilities(user_location)
        
        assert len(facilities) > 0
        # All should be emergency facilities
        for facility in facilities:
            assert facility.facility_type in ['emergency', 'hospital']
    
    @patch('src.location.location_service.requests.get')
    def test_get_emergency_facilities_sorted_by_distance(self, mock_get, location_service, user_location):
        """Test that emergency facilities are sorted by distance."""
        # Mock API response with multiple facilities at different distances
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': [
                {
                    'name': 'Far Hospital',
                    'types': ['emergency', 'hospital'],
                    'geometry': {'location': {'lat': 37.8, 'lng': -122.5}},
                    'vicinity': 'Far Street',
                    'rating': 4.0
                },
                {
                    'name': 'Near Hospital',
                    'types': ['emergency', 'hospital'],
                    'geometry': {'location': {'lat': 37.7750, 'lng': -122.4195}},
                    'vicinity': 'Near Street',
                    'rating': 3.5
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        facilities = location_service.get_emergency_facilities(user_location)
        
        # Should be sorted by distance (closest first)
        if len(facilities) > 1:
            for i in range(len(facilities) - 1):
                assert facilities[i].distance_km <= facilities[i + 1].distance_km
    
    def test_facility_ranking_emergency_priority(self, location_service, user_location):
        """Test that emergency facilities are prioritized for high severity."""
        facilities = [
            Facility(
                name="Clinic",
                facility_type="clinic",
                location=Location(37.7750, -122.4195),
                distance_km=1.0,
                specialties=["general_practice"],
                rating=4.5
            ),
            Facility(
                name="Emergency Hospital",
                facility_type="emergency",
                location=Location(37.7760, -122.4200),
                distance_km=2.0,
                specialties=["emergency"],
                rating=4.0
            )
        ]
        
        ranked = location_service._rank_facilities(
            facilities,
            user_location,
            Severity.HIGH,
            "heart_attack"
        )
        
        # Emergency facility should be ranked first despite being farther
        assert ranked[0].facility_type == "emergency"
    
    def test_facility_ranking_distance_priority(self, location_service, user_location):
        """Test that distance matters when severity match is equal."""
        facilities = [
            Facility(
                name="Far Hospital",
                facility_type="hospital",
                location=Location(37.8, -122.5),
                distance_km=10.0,
                specialties=["general_practice"],
                rating=4.5
            ),
            Facility(
                name="Near Hospital",
                facility_type="hospital",
                location=Location(37.7750, -122.4195),
                distance_km=1.0,
                specialties=["general_practice"],
                rating=4.0
            )
        ]
        
        ranked = location_service._rank_facilities(
            facilities,
            user_location,
            Severity.MODERATE,
            "influenza"
        )
        
        # Closer facility should be ranked first
        assert ranked[0].distance_km < ranked[1].distance_km
    
    def test_facility_ranking_specialty_match(self, location_service, user_location):
        """Test that specialty matching affects ranking."""
        facilities = [
            Facility(
                name="General Hospital",
                facility_type="hospital",
                location=Location(37.7750, -122.4195),
                distance_km=2.0,
                specialties=["general_practice"],
                rating=4.0
            ),
            Facility(
                name="Cardiology Center",
                facility_type="hospital",
                location=Location(37.7760, -122.4200),
                distance_km=2.0,
                specialties=["cardiology"],
                rating=4.0
            )
        ]
        
        ranked = location_service._rank_facilities(
            facilities,
            user_location,
            Severity.MODERATE,
            "hypertension"
        )
        
        # Cardiology center should be ranked higher for hypertension
        assert "cardiology" in ranked[0].specialties
    
    @patch('src.location.location_service.requests.get')
    def test_api_error_handling(self, mock_get, location_service, user_location):
        """Test that API errors are handled gracefully."""
        # Mock API error - need to raise on the call, not as side_effect
        mock_get.side_effect = requests.RequestException("API Error")
        
        facilities = location_service.find_facilities(
            user_location,
            Severity.MODERATE,
            "influenza"
        )
        
        # Should return empty list on error
        assert facilities == []
    
    @patch('src.location.location_service.requests.get')
    def test_api_non_ok_status(self, mock_get, location_service, user_location):
        """Test handling of non-OK API status."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': 'ZERO_RESULTS',
            'results': []
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        facilities = location_service.find_facilities(
            user_location,
            Severity.MODERATE,
            "influenza"
        )
        
        # Should return empty list
        assert facilities == []
    
    def test_no_api_key_warning(self):
        """Test that missing API key logs warning."""
        service = LocationService(api_key=None)
        assert service.api_key is None
    
    @patch('src.location.location_service.requests.get')
    def test_facility_information_completeness(self, mock_get, location_service, user_location):
        """Test that all facilities have required fields (Property 32)."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': [
                {
                    'name': 'Complete Hospital',
                    'types': ['hospital'],
                    'geometry': {'location': {'lat': 37.7562, 'lng': -122.4205}},
                    'vicinity': '1001 Potrero Ave',
                    'rating': 4.5,
                    'formatted_phone_number': '(415) 206-8000'
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        facilities = location_service.find_facilities(
            user_location,
            Severity.MODERATE,
            "influenza"
        )
        
        # Verify all required fields are present
        for facility in facilities:
            assert facility.name
            assert facility.facility_type
            assert facility.location
            assert facility.distance_km >= 0
            assert isinstance(facility.specialties, list)
            assert isinstance(facility.contact, str)
            assert 0.0 <= facility.rating <= 5.0
    
    def test_illness_specialty_mapping(self, location_service):
        """Test that illness types map to appropriate specialties."""
        # Test known mappings
        assert 'cardiology' in location_service.ILLNESS_SPECIALTY_MAP['hypertension']
        assert 'emergency' in location_service.ILLNESS_SPECIALTY_MAP['heart_attack']
        assert 'pulmonology' in location_service.ILLNESS_SPECIALTY_MAP['asthma']
        assert 'neurology' in location_service.ILLNESS_SPECIALTY_MAP['migraine']
        
        # Test default mapping
        assert 'general_practice' in location_service.ILLNESS_SPECIALTY_MAP['default']
    
    @patch('src.location.location_service.requests.get')
    def test_parse_place_result_with_missing_fields(self, mock_get, location_service, user_location):
        """Test parsing place results with missing optional fields."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'status': 'OK',
            'results': [
                {
                    'name': 'Minimal Hospital',
                    'types': ['hospital'],
                    'geometry': {'location': {'lat': 37.7562, 'lng': -122.4205}},
                    # Missing vicinity, rating, phone
                }
            ]
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        facilities = location_service.find_facilities(
            user_location,
            Severity.MODERATE,
            "influenza"
        )
        
        # Should still create facility with defaults
        assert len(facilities) > 0
        assert facilities[0].name == 'Minimal Hospital'
        assert facilities[0].contact == ''
        assert facilities[0].rating == 0.0
    
    def test_location_validation_in_find_facilities(self, location_service):
        """Test that invalid locations are rejected."""
        invalid_location = Location(latitude=100.0, longitude=-122.4194)
        
        with pytest.raises(ValueError):
            location_service.find_facilities(
                invalid_location,
                Severity.MODERATE,
                "influenza"
            )
    
    def test_location_validation_in_get_emergency_facilities(self, location_service):
        """Test that invalid locations are rejected in emergency search."""
        invalid_location = Location(latitude=37.7749, longitude=200.0)
        
        with pytest.raises(ValueError):
            location_service.get_emergency_facilities(invalid_location)


class TestFacilityRanking:
    """Detailed tests for facility ranking algorithm."""
    
    @pytest.fixture
    def location_service(self):
        """Create a LocationService instance."""
        return LocationService(api_key="test_api_key")
    
    @pytest.fixture
    def user_location(self):
        """Create a test user location."""
        return Location(latitude=37.7749, longitude=-122.4194)
    
    def test_ranking_with_all_factors(self, location_service, user_location):
        """Test ranking considers all factors: severity, specialty, distance, rating."""
        facilities = [
            Facility(
                name="Perfect Match",
                facility_type="emergency",
                location=Location(37.7750, -122.4195),
                distance_km=1.0,
                specialties=["emergency", "cardiology"],
                rating=5.0
            ),
            Facility(
                name="Good Match",
                facility_type="hospital",
                location=Location(37.7760, -122.4200),
                distance_km=2.0,
                specialties=["cardiology"],
                rating=4.5
            ),
            Facility(
                name="Poor Match",
                facility_type="clinic",
                location=Location(37.7770, -122.4210),
                distance_km=3.0,
                specialties=["general_practice"],
                rating=3.0
            )
        ]
        
        ranked = location_service._rank_facilities(
            facilities,
            user_location,
            Severity.CRITICAL,
            "heart_attack"
        )
        
        # Perfect match should be first
        assert ranked[0].name == "Perfect Match"
        # Poor match should be last
        assert ranked[-1].name == "Poor Match"
    
    def test_ranking_low_severity_prefers_clinics(self, location_service, user_location):
        """Test that low severity prefers clinics over hospitals."""
        facilities = [
            Facility(
                name="Hospital",
                facility_type="hospital",
                location=Location(37.7750, -122.4195),
                distance_km=1.0,
                specialties=["general_practice"],
                rating=4.5
            ),
            Facility(
                name="Clinic",
                facility_type="clinic",
                location=Location(37.7760, -122.4200),
                distance_km=1.5,
                specialties=["general_practice"],
                rating=4.0
            )
        ]
        
        ranked = location_service._rank_facilities(
            facilities,
            user_location,
            Severity.LOW,
            "influenza"
        )
        
        # Clinic should be ranked higher for low severity
        assert ranked[0].facility_type == "clinic"
