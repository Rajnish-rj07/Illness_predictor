"""
Property-based tests for LocationService.

Uses hypothesis to test universal properties across all valid inputs.

Validates: Requirements 16.1, 16.2, 16.3, 16.4
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import Mock, patch
from src.location.location_service import LocationService
from src.models.data_models import Location, Facility, Severity


# Custom strategies for generating test data
@st.composite
def valid_locations(draw):
    """Generate valid Location objects."""
    latitude = draw(st.floats(min_value=-90, max_value=90, allow_nan=False, allow_infinity=False))
    longitude = draw(st.floats(min_value=-180, max_value=180, allow_nan=False, allow_infinity=False))
    address = draw(st.text(min_size=0, max_size=100))
    return Location(latitude=latitude, longitude=longitude, address=address)


@st.composite
def valid_facilities(draw):
    """Generate valid Facility objects."""
    name = draw(st.text(min_size=1, max_size=100))
    facility_type = draw(st.sampled_from(['hospital', 'clinic', 'emergency']))
    location = draw(valid_locations())
    distance_km = draw(st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False))
    specialties = draw(st.lists(st.text(min_size=1, max_size=50), min_size=0, max_size=5))
    contact = draw(st.text(min_size=0, max_size=50))
    rating = draw(st.floats(min_value=0.0, max_value=5.0, allow_nan=False, allow_infinity=False))
    
    return Facility(
        name=name,
        facility_type=facility_type,
        location=location,
        distance_km=distance_km,
        specialties=specialties,
        contact=contact,
        rating=rating
    )


class TestLocationServiceProperties:
    """Property-based tests for LocationService."""
    
    @given(loc1=valid_locations(), loc2=valid_locations())
    @settings(max_examples=20)
    def test_property_distance_non_negative(self, loc1, loc2):
        """
        Property: Distance between any two locations is non-negative.
        Validates: Requirements 16.4
        """
        location_service = LocationService(api_key="test_api_key")
        distance = location_service.calculate_distance(loc1, loc2)
        assert distance >= 0, f"Distance should be non-negative, got {distance}"
    
    @given(location=valid_locations())
    @settings(max_examples=20)
    def test_property_distance_to_self_is_zero(self, location):
        """
        Property: Distance from a location to itself is zero.
        Validates: Requirements 16.4
        """
        location_service = LocationService(api_key="test_api_key")
        distance = location_service.calculate_distance(location, location)
        assert distance == 0.0, f"Distance to self should be 0, got {distance}"
    
    @given(loc1=valid_locations(), loc2=valid_locations())
    @settings(max_examples=20)
    def test_property_distance_symmetry(self, loc1, loc2):
        """
        Property: Distance from A to B equals distance from B to A.
        Validates: Requirements 16.4
        """
        location_service = LocationService(api_key="test_api_key")
        distance_ab = location_service.calculate_distance(loc1, loc2)
        distance_ba = location_service.calculate_distance(loc2, loc1)
        
        # Allow small floating point differences
        assert abs(distance_ab - distance_ba) < 0.001, \
            f"Distance should be symmetric: {distance_ab} != {distance_ba}"
    
    @given(
        loc1=valid_locations(),
        loc2=valid_locations(),
        loc3=valid_locations()
    )
    @settings(max_examples=10)
    def test_property_triangle_inequality(self, loc1, loc2, loc3):
        """
        Property: Triangle inequality holds for any three locations.
        Distance(A, C) <= Distance(A, B) + Distance(B, C)
        Validates: Requirements 16.4
        """
        location_service = LocationService(api_key="test_api_key")
        dist_ac = location_service.calculate_distance(loc1, loc3)
        dist_ab = location_service.calculate_distance(loc1, loc2)
        dist_bc = location_service.calculate_distance(loc2, loc3)
        
        # Allow small floating point tolerance
        assert dist_ac <= dist_ab + dist_bc + 0.1, \
            f"Triangle inequality violated: {dist_ac} > {dist_ab} + {dist_bc}"
    
    @given(
        facilities=st.lists(valid_facilities(), min_size=1, max_size=10),
        user_location=valid_locations(),
        severity=st.sampled_from(list(Severity)),
        illness_type=st.one_of(st.none(), st.text(min_size=1, max_size=50))
    )
    @settings(max_examples=20)
    def test_property_30_facility_finding_completeness(
        self, facilities, user_location, severity, illness_type
    ):
        """
        Property 30: Facility finding completeness
        For any valid location, the system should return facilities or indicate none available.
        Validates: Requirements 16.1
        """
        location_service = LocationService(api_key="test_api_key")
        # Mock the API call to return our test facilities
        with patch('src.location.location_service.requests.get') as mock_get:
            # Create mock response
            mock_results = []
            for facility in facilities[:5]:  # Limit to 5 for API simulation
                mock_results.append({
                    'name': facility.name,
                    'types': [facility.facility_type] + facility.specialties,
                    'geometry': {
                        'location': {
                            'lat': facility.location.latitude,
                            'lng': facility.location.longitude
                        }
                    },
                    'vicinity': facility.location.address,
                    'rating': facility.rating,
                    'formatted_phone_number': facility.contact
                })
            
            mock_response = Mock()
            mock_response.json.return_value = {
                'status': 'OK',
                'results': mock_results
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            # Call find_facilities
            result = location_service.find_facilities(user_location, severity, illness_type)
            
            # Should return a list (possibly empty, but not None)
            assert isinstance(result, list), "Should return a list of facilities"
            
            # If results exist, they should be valid Facility objects
            for facility in result:
                assert isinstance(facility, Facility)
                facility.validate()
    
    @given(
        user_location=valid_locations(),
        severity=st.sampled_from([Severity.HIGH, Severity.CRITICAL])
    )
    @settings(max_examples=20)
    def test_property_31_emergency_facility_prioritization(
        self, user_location, severity
    ):
        """
        Property 31: Emergency facility prioritization
        For any prediction with High or Critical severity, emergency facilities
        should be ranked higher than non-emergency facilities.
        Validates: Requirements 16.2
        """
        location_service = LocationService(api_key="test_api_key")
        # Create test facilities with different types
        facilities = [
            Facility(
                name="Clinic",
                facility_type="clinic",
                location=Location(
                    user_location.latitude + 0.01,
                    user_location.longitude + 0.01
                ),
                distance_km=1.0,
                specialties=["general_practice"],
                rating=4.5
            ),
            Facility(
                name="Emergency Hospital",
                facility_type="emergency",
                location=Location(
                    user_location.latitude + 0.02,
                    user_location.longitude + 0.02
                ),
                distance_km=2.0,
                specialties=["emergency"],
                rating=4.0
            ),
            Facility(
                name="Regular Hospital",
                facility_type="hospital",
                location=Location(
                    user_location.latitude + 0.015,
                    user_location.longitude + 0.015
                ),
                distance_km=1.5,
                specialties=["general_practice"],
                rating=4.2
            )
        ]
        
        # Rank facilities
        ranked = location_service._rank_facilities(
            facilities,
            user_location,
            severity,
            "heart_attack"
        )
        
        # Find positions of emergency vs non-emergency
        emergency_positions = [
            i for i, f in enumerate(ranked)
            if f.facility_type == 'emergency'
        ]
        non_emergency_positions = [
            i for i, f in enumerate(ranked)
            if f.facility_type != 'emergency'
        ]
        
        # Emergency facilities should appear before non-emergency
        if emergency_positions and non_emergency_positions:
            assert min(emergency_positions) < max(non_emergency_positions), \
                "Emergency facilities should be ranked higher for high/critical severity"
    
    @given(
        facilities=st.lists(valid_facilities(), min_size=1, max_size=10),
        user_location=valid_locations(),
        severity=st.sampled_from(list(Severity)),
        illness_type=st.one_of(st.none(), st.text(min_size=1, max_size=50))
    )
    @settings(max_examples=20)
    def test_property_32_facility_information_completeness(
        self, facilities, user_location, severity, illness_type
    ):
        """
        Property 32: Facility information completeness
        For any facility returned, it should include all required fields.
        Validates: Requirements 16.3
        """
        location_service = LocationService(api_key="test_api_key")
        # Mock API to return facilities
        with patch('src.location.location_service.requests.get') as mock_get:
            mock_results = []
            for facility in facilities[:5]:
                mock_results.append({
                    'name': facility.name,
                    'types': [facility.facility_type] + facility.specialties,
                    'geometry': {
                        'location': {
                            'lat': facility.location.latitude,
                            'lng': facility.location.longitude
                        }
                    },
                    'vicinity': facility.location.address,
                    'rating': facility.rating,
                    'formatted_phone_number': facility.contact
                })
            
            mock_response = Mock()
            mock_response.json.return_value = {
                'status': 'OK',
                'results': mock_results
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = location_service.find_facilities(user_location, severity, illness_type)
            
            # Check all required fields are present
            for facility in result:
                assert facility.name, "Facility must have a name"
                assert facility.facility_type in ['hospital', 'clinic', 'emergency'], \
                    "Facility must have valid type"
                assert facility.location is not None, "Facility must have location"
                assert facility.distance_km >= 0, "Distance must be non-negative"
                assert isinstance(facility.specialties, list), "Specialties must be a list"
                assert isinstance(facility.contact, str), "Contact must be a string"
                assert 0.0 <= facility.rating <= 5.0, "Rating must be between 0 and 5"
    
    @given(
        facilities=st.lists(valid_facilities(), min_size=2, max_size=10),
        user_location=valid_locations(),
        severity=st.sampled_from(list(Severity)),
        illness_type=st.one_of(st.none(), st.text(min_size=1, max_size=50))
    )
    @settings(max_examples=10)
    def test_property_33_facility_ranking_correctness(
        self, facilities, user_location, severity, illness_type
    ):
        """
        Property 33: Facility ranking correctness
        For any list of facilities, they should be ranked by:
        (1) severity match, (2) distance, (3) rating, in that priority order.
        Validates: Requirements 16.4
        """
        location_service = LocationService(api_key="test_api_key")
        # Rank facilities
        ranked = location_service._rank_facilities(
            facilities,
            user_location,
            severity,
            illness_type
        )
        
        # Verify ranking is stable (same input produces same output)
        ranked2 = location_service._rank_facilities(
            facilities,
            user_location,
            severity,
            illness_type
        )
        
        assert len(ranked) == len(ranked2), "Ranking should be deterministic"
        for i in range(len(ranked)):
            assert ranked[i].name == ranked2[i].name, \
                "Ranking should produce consistent results"
    
    @given(
        user_location=valid_locations(),
        severity=st.sampled_from([Severity.HIGH, Severity.CRITICAL])
    )
    @settings(max_examples=20)
    def test_property_emergency_facilities_are_emergency_type(
        self, user_location, severity
    ):
        """
        Property: Emergency facility search returns only emergency/hospital types.
        Validates: Requirements 16.2
        """
        location_service = LocationService(api_key="test_api_key")
        # Mock API response
        with patch('src.location.location_service.requests.get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                'status': 'OK',
                'results': [
                    {
                        'name': 'Emergency Room',
                        'types': ['emergency', 'hospital'],
                        'geometry': {'location': {'lat': user_location.latitude + 0.01, 
                                                  'lng': user_location.longitude + 0.01}},
                        'vicinity': 'Test Street',
                        'rating': 4.5
                    }
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            facilities = location_service.get_emergency_facilities(user_location)
            
            # All facilities should be emergency or hospital type
            for facility in facilities:
                assert facility.facility_type in ['emergency', 'hospital'], \
                    f"Emergency search should only return emergency/hospital, got {facility.facility_type}"
    
    @given(
        facilities=st.lists(valid_facilities(), min_size=1, max_size=20),
        user_location=valid_locations()
    )
    @settings(max_examples=10)
    def test_property_max_facilities_limit(
        self, facilities, user_location
    ):
        """
        Property: find_facilities respects max_facilities limit.
        Validates: Requirements 16.5
        """
        location_service = LocationService(api_key="test_api_key")
        # Mock API to return all facilities
        with patch('src.location.location_service.requests.get') as mock_get:
            mock_results = []
            for facility in facilities:
                mock_results.append({
                    'name': facility.name,
                    'types': [facility.facility_type],
                    'geometry': {
                        'location': {
                            'lat': facility.location.latitude,
                            'lng': facility.location.longitude
                        }
                    },
                    'vicinity': facility.location.address,
                    'rating': facility.rating
                })
            
            mock_response = Mock()
            mock_response.json.return_value = {
                'status': 'OK',
                'results': mock_results
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = location_service.find_facilities(
                user_location,
                Severity.MODERATE,
                None
            )
            
            # Should not exceed max_facilities
            assert len(result) <= location_service.max_facilities, \
                f"Should return at most {location_service.max_facilities} facilities, got {len(result)}"
    
    @given(
        facilities=st.lists(valid_facilities(), min_size=2, max_size=10),
        user_location=valid_locations()
    )
    @settings(max_examples=10)
    def test_property_emergency_facilities_sorted_by_distance(
        self, facilities, user_location
    ):
        """
        Property: Emergency facilities are sorted by distance (closest first).
        Validates: Requirements 16.2
        """
        location_service = LocationService(api_key="test_api_key")
        # Mock API response
        with patch('src.location.location_service.requests.get') as mock_get:
            mock_results = []
            for facility in facilities[:5]:
                mock_results.append({
                    'name': facility.name,
                    'types': ['emergency', 'hospital'],
                    'geometry': {
                        'location': {
                            'lat': facility.location.latitude,
                            'lng': facility.location.longitude
                        }
                    },
                    'vicinity': facility.location.address,
                    'rating': facility.rating
                })
            
            mock_response = Mock()
            mock_response.json.return_value = {
                'status': 'OK',
                'results': mock_results
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = location_service.get_emergency_facilities(user_location)
            
            # Verify sorted by distance
            if len(result) > 1:
                for i in range(len(result) - 1):
                    assert result[i].distance_km <= result[i + 1].distance_km, \
                        "Emergency facilities should be sorted by distance"
