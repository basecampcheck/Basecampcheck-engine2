import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing Supabase credentials in Railway.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ACTIVITY_STAYS = [
    # === ALBERTA & BC ===
    {
        "name": "Mount Kidd RV Park",
        "provider_network": "independent",
        "external_facility_id": "mount-kidd-kananaskis",
        "state_province": "AB",
        "country": "CA",
        "latitude": 50.8493,
        "longitude": -115.1492,
        "booking_url": "https://www.mountkiddrv.com/",
        "golf_on_site": False,
        "primary_activity": "Skiing",
        "ski_nearby": True,
        "fishing": False,
        "boating": False,
        "activities": ["Skiing", "Hiking", "Biking", "Tennis"]
    },
    {
        "name": "Dinosaur Provincial Park Campground",
        "provider_network": "alberta_parks",
        "external_facility_id": "dinosaur-pp-ab",
        "state_province": "AB",
        "country": "CA",
        "latitude": 50.7570,
        "longitude": -111.5170,
        "booking_url": "https://albertaparks.ca/",
        "golf_on_site": False,
        "primary_activity": "Hiking",
        "ski_nearby": False,
        "fishing": False,
        "boating": True,
        "activities": ["Hiking", "Fossil Hunting", "Paddling"]
    },
    {
        "name": "Fairmont Hot Springs RV Resort",
        "provider_network": "independent",
        "external_facility_id": "fairmont-hot-springs-bc",
        "state_province": "BC",
        "country": "CA",
        "latitude": 50.3347,
        "longitude": -115.8617,
        "booking_url": "https://www.fairmonthotsprings.com/rv-resort/",
        "golf_on_site": True,
        "primary_activity": "Golf",
        "ski_nearby": True,
        "fishing": False,
        "boating": False,
        "activities": ["Golf", "Skiing", "Hot Springs"]
    },
    {
        "name": "Whistler RV Park and Campground",
        "provider_network": "independent",
        "external_facility_id": "whistler-rv-park-bc",
        "state_province": "BC",
        "country": "CA",
        "latitude": 50.0463,
        "longitude": -123.0883,
        "booking_url": "https://whistlerrvpark.com/",
        "golf_on_site": False,
        "primary_activity": "Skiing",
        "ski_nearby": True,
        "fishing": False,
        "boating": False,
        "activities": ["Skiing", "Snowboarding", "Mountain Biking"]
    },
    {
        "name": "Burnaby Cariboo RV Park",
        "provider_network": "independent",
        "external_facility_id": "burnaby-cariboo-rv",
        "state_province": "BC",
        "country": "CA",
        "latitude": 49.2394,
        "longitude": -122.9157,
        "booking_url": "https://www.bcrvpark.com/",
        "golf_on_site": False,
        "primary_activity": "City Cycling",
        "ski_nearby": False,
        "fishing": False,
        "boating": False,
        "activities": ["Cycling", "Hiking", "Sightseeing"]
    },

    # === CALIFORNIA ===
    {
        "name": "The Springs at Borrego RV Resort & Golf",
        "provider_network": "independent",
        "external_facility_id": "springs-at-borrego-ca",
        "state_province": "CA",
        "country": "US",
        "latitude": 33.2656,
        "longitude": -116.3422,
        "booking_url": "https://www.springsatborrego.com/",
        "golf_on_site": True,
        "primary_activity": "Golf",
        "ski_nearby": False,
        "fishing": True,
        "boating": False,
        "activities": ["Golf", "Stargazing", "Fishing"]
    },
    {
        "name": "Likely Place Golf & RV Resort",
        "provider_network": "independent",
        "external_facility_id": "likely-place-ca",
        "state_province": "CA",
        "country": "US",
        "latitude": 41.2299,
        "longitude": -120.5055,
        "booking_url": "https://likelyplace.com/",
        "golf_on_site": True,
        "primary_activity":"
