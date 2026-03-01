"""
Location Service for finding nearby healthcare facilities.

This service integrates with Google Places API to find healthcare facilities
based on user location and prediction severity. It implements facility ranking
based on severity match, distance, and rating.

Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5
"""

import logging
import math
from typing import List, Optional
import requests
from config.settings import settings
from src.models.data_models import Location, Facility, Severity

logger = logging.getLogger(__name__)


class LocationService:
    """
    Service for finding and ranking nearby healthcare facilities.
    
    Integrates with Google Places API to search for hospitals, clinics,
    and emergency facilities based on user location and illness severity.
    """
    
    # Specialty mappings for different illness types
    ILLNESS_SPECIALTY_MAP = {
        'influenza': ['general_practice', 'internal_medicine'],
        'pneumonia': ['pulmonology', 'internal_medicine', 'emergency'],
        'bronchitis': ['pulmonology', 'general_practice'],
        'asthma': ['pulmonology', 'allergy'],
        'migraine': ['neurology', 'general_practice'],
        'meningitis': ['neurology', 'emergency', 'infectious_disease'],
        'diabetes': ['endocrinology', 'internal_medicine'],
        'hypertension': ['cardiology', 'internal_medicine'],
        'gastroenteritis': ['gastroenterology', 'general_practice'],
        'appendicitis': ['surgery', 'emergency'],
        'heart_attack': ['cardiology', 'emergency'],
        'stroke': ['neurology', 'emergency'],
        'default': ['general_practice', 'internal_medicine']
    }
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the LocationService.
        
        Args:
            api_key: Google Places API key. If None, uses settings.
        """
        self.api_key = api_key or settings.google_places_api_key
        self.search_radius_km = settings.facility_search_radius_km
        self.max_facilities = settings.max_facilities_returned
        self.base_url = "https://maps.googleapis.com/maps/api/place"
        
        if not self.api_key:
            logger.warning("Google Places API key not configured. Location service will not function.")
    
    def find_facilities(
        self,
        location: Location,
        severity: Severity,
        illness_type: Optional[str] = None
    ) -> List[Facility]:
        """
        Find nearby healthcare facilities based on location and severity.
        
        Implements the facility ranking algorithm:
        1. Filter facilities by specialty matching illness type
        2. Calculate distance from user location
        3. Prioritize emergency facilities for Critical severity
        4. Rank by: severity match > distance > rating
        5. Return top facilities
        
        Args:
            location: User's geographic location
            severity: Severity of the predicted illness
            illness_type: Type of illness for specialty matching (optional)
        
        Returns:
            List of ranked Facility objects (up to max_facilities)
        
        Validates: Requirements 16.1, 16.4, 16.5
        """
        logger.info(f"Finding facilities for location ({location.latitude}, {location.longitude}), "
                   f"severity={severity.value}, illness_type={illness_type}")
        
        # Validate location
        location.validate()
        
        # For critical severity, prioritize emergency facilities
        if severity == Severity.CRITICAL:
            return self.get_emergency_facilities(location)
        
        # Search for healthcare facilities
        facilities = self._search_places(location, severity, illness_type)
        
        # Rank facilities
        ranked_facilities = self._rank_facilities(facilities, location, severity, illness_type)
        
        # Return top N facilities
        return ranked_facilities[:self.max_facilities]
    
    def get_emergency_facilities(self, location: Location) -> List[Facility]:
        """
        Get emergency facilities near the given location.
        
        Prioritizes emergency rooms and hospitals with emergency departments.
        
        Args:
            location: User's geographic location
        
        Returns:
            List of emergency facilities ranked by distance
        
        Validates: Requirements 16.2
        """
        logger.info(f"Finding emergency facilities for location ({location.latitude}, {location.longitude})")
        
        # Validate location
        location.validate()
        
        # Search specifically for emergency facilities
        facilities = self._search_places(location, Severity.CRITICAL, None, emergency_only=True)
        
        # Sort by distance (closest first)
        facilities.sort(key=lambda f: f.distance_km)
        
        return facilities[:self.max_facilities]
    
    def calculate_distance(self, loc1: Location, loc2: Location) -> float:
        """
        Calculate distance between two locations using Haversine formula.
        
        Args:
            loc1: First location
            loc2: Second location
        
        Returns:
            Distance in kilometers
        
        Validates: Requirements 16.4
        """
        # Validate locations
        loc1.validate()
        loc2.validate()
        
        # Earth's radius in kilometers
        R = 6371.0
        
        # Convert to radians
        lat1_rad = math.radians(loc1.latitude)
        lon1_rad = math.radians(loc1.longitude)
        lat2_rad = math.radians(loc2.latitude)
        lon2_rad = math.radians(loc2.longitude)
        
        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        distance = R * c
        
        return distance
    
    def _search_places(
        self,
        location: Location,
        severity: Severity,
        illness_type: Optional[str],
        emergency_only: bool = False
    ) -> List[Facility]:
        """
        Search for healthcare facilities using Google Places API.
        
        Args:
            location: User's location
            severity: Illness severity
            illness_type: Type of illness
            emergency_only: If True, search only for emergency facilities
        
        Returns:
            List of Facility objects
        """
        if not self.api_key:
            logger.error("Cannot search places: API key not configured")
            return []
        
        # Determine search type based on severity and emergency_only flag
        if emergency_only or severity == Severity.CRITICAL:
            search_type = "emergency"
        elif severity == Severity.HIGH:
            search_type = "hospital"
        else:
            search_type = "hospital|clinic"
        
        # Convert radius to meters for API
        radius_meters = self.search_radius_km * 1000
        
        # Build API request
        url = f"{self.base_url}/nearbysearch/json"
        params = {
            'location': f"{location.latitude},{location.longitude}",
            'radius': radius_meters,
            'type': search_type,
            'key': self.api_key
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get('status') != 'OK':
                logger.warning(f"Google Places API returned status: {data.get('status')}")
                return []
            
            # Parse results into Facility objects
            facilities = []
            for place in data.get('results', []):
                facility = self._parse_place_result(place, location)
                if facility:
                    facilities.append(facility)
            
            logger.info(f"Found {len(facilities)} facilities")
            return facilities
            
        except requests.RequestException as e:
            logger.error(f"Error searching places: {e}")
            return []
    
    def _parse_place_result(self, place: dict, user_location: Location) -> Optional[Facility]:
        """
        Parse a Google Places API result into a Facility object.
        
        Args:
            place: Place result from API
            user_location: User's location for distance calculation
        
        Returns:
            Facility object or None if parsing fails
        """
        try:
            # Extract location
            place_location = place.get('geometry', {}).get('location', {})
            facility_location = Location(
                latitude=place_location.get('lat', 0.0),
                longitude=place_location.get('lng', 0.0),
                address=place.get('vicinity', '')
            )
            
            # Calculate distance
            distance = self.calculate_distance(user_location, facility_location)
            
            # Determine facility type
            types = place.get('types', [])
            if 'hospital' in types:
                facility_type = 'hospital'
            elif 'emergency' in types or 'emergency_room' in types:
                facility_type = 'emergency'
            else:
                facility_type = 'clinic'
            
            # Extract specialties from types
            specialties = [t for t in types if t not in ['point_of_interest', 'establishment', 'health']]
            
            # Create Facility object
            facility = Facility(
                name=place.get('name', 'Unknown Facility'),
                facility_type=facility_type,
                location=facility_location,
                distance_km=distance,
                specialties=specialties,
                contact=place.get('formatted_phone_number', ''),
                rating=place.get('rating', 0.0)
            )
            
            return facility
            
        except Exception as e:
            logger.error(f"Error parsing place result: {e}")
            return None
    
    def _rank_facilities(
        self,
        facilities: List[Facility],
        user_location: Location,
        severity: Severity,
        illness_type: Optional[str]
    ) -> List[Facility]:
        """
        Rank facilities based on severity match, distance, and rating.
        
        Ranking algorithm:
        1. Emergency facilities get highest priority for High/Critical severity
        2. Specialty match for the illness type
        3. Distance from user (closer is better)
        4. Facility rating
        
        Args:
            facilities: List of facilities to rank
            user_location: User's location
            severity: Illness severity
            illness_type: Type of illness
        
        Returns:
            Sorted list of facilities
        
        Validates: Requirements 16.4
        """
        # Get relevant specialties for the illness
        specialties = self.ILLNESS_SPECIALTY_MAP.get(
            illness_type.lower() if illness_type else 'default',
            self.ILLNESS_SPECIALTY_MAP['default']
        )
        
        def calculate_score(facility: Facility) -> tuple:
            """
            Calculate ranking score for a facility.
            Returns tuple for sorting: (severity_match, -distance, rating)
            """
            # Severity match score (higher is better)
            severity_score = 0
            if severity in [Severity.HIGH, Severity.CRITICAL]:
                if facility.facility_type == 'emergency':
                    severity_score = 3
                elif facility.facility_type == 'hospital':
                    severity_score = 2
                else:
                    severity_score = 1
            else:
                if facility.facility_type == 'clinic':
                    severity_score = 3
                elif facility.facility_type == 'hospital':
                    severity_score = 2
                else:
                    severity_score = 1
            
            # Specialty match score
            specialty_score = 0
            for specialty in specialties:
                if specialty in facility.specialties:
                    specialty_score += 1
            
            # Combined severity and specialty score
            match_score = severity_score * 10 + specialty_score
            
            # Distance (negative for sorting, closer is better)
            distance_score = -facility.distance_km
            
            # Rating
            rating_score = facility.rating
            
            return (match_score, distance_score, rating_score)
        
        # Sort facilities by score (descending)
        ranked = sorted(facilities, key=calculate_score, reverse=True)
        
        logger.info(f"Ranked {len(ranked)} facilities")
        return ranked
