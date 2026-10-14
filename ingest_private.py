import os
from supabase import create_client

# Connect to Supabase using Railway environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing Supabase credentials in Railway.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# A consolidated master batch of premier private RV, Glamping, and KOA resorts across the US and Canada
PRIVATE_RESORTS = [
    # --- CAMPSPOT NETWORKS ---
    {
        "name": "Sun Outdoors Rocky Mountains",
        "provider_network": "campspot",
        "external_facility_id": "sun-outdoors-rocky-mountains",
        "state_province": "CO",
        "country": "US",
        "latitude": 40.1585,
        "longitude": -105.9525,
        "total_sites_count": 300,
        "booking_url": "https://www.campspot.com/book/sun-outdoors-rocky-mountains",
        "golf_on_site": False,
        "electric_amps": [30, 50],
        "water_hookup": True
    },
    {
        "name": "Moab Valley RV Resort & Campground",
        "provider_network": "campspot",
        "external_facility_id": "moab-valley-rv-resort",
        "state_province": "UT",
        "country": "US",
        "latitude": 38.5919,
        "longitude": -109.5684,
        "total_sites_count": 150,
        "booking_url": "https://www.campspot.com/book/moab-valley-rv-resort",
        "golf_on_site": False,
        "electric_amps": [30, 50],
        "water_hookup": True
    },
    {
        "name": "Oceanside RV Resort & Campground",
        "provider_network": "campspot",
        "external_facility_id": "oceanside-rv-resort",
        "state_province": "BC",
        "country": "CA",
        "latitude": 48.6015,
        "longitude": -123.3888,
        "total_sites_count": 120,
        "booking_url": "https://www.campspot.com/book/oceanside-rv-resort",
        "golf_on_site": False,
        "electric_amps": [30, 50],
        "water_hookup": True
    },
    {
        "name": "Tiger Run Resort",
        "provider_network": "campspot",
        "external_facility_id": "tiger-run-resort",
        "state_province": "CO",
        "country": "US",
        "latitude": 39.5186,
        "longitude": -106.0461,
        "total_sites_count": 250,
        "booking_url": "https://www.campspot.com/book/tiger-run-resort",
        "golf_on_site": False,
        "electric_amps": [30, 50],
        "water_hookup": True
    },
    {
        "name": "Under Canvas Zion (Glamping)",
        "provider_network": "campspot",
        "external_facility_id": "under-canvas-zion",
        "state_province": "UT",
        "country": "US",
        "latitude": 37.2622,
        "longitude": -113.1235,
        "total_sites_count": 80,
        "booking_url": "https://www.campspot.com/book/under-canvas-zion",
        "golf_on_site": False,
        "electric_amps": [],
        "water_hookup": False
    },
    {
        "name": "Camp Fimfo Texas Hill Country",
        "provider_network": "campspot",
        "external_facility_id": "camp-fimfo-texas-hill-country",
        "state_province": "TX",
        "country": "US",
        "latitude": 29.8335,
        "longitude": -98.1561,
        "total_sites_count": 200,
        "booking_url": "https://www.campspot.com/book/camp-fimfo-texas-hill-country",
        "golf_on_site": False,
        "electric_amps": [30, 50],
        "water_hookup": True
    },
    
    # --- KOA NETWORKS ---
    {
        "name": "Grand Canyon South Rim KOA Holiday",
        "provider_network": "koa",
        "external_facility_id": "grand-canyon-koa",
        "state_province": "AZ",
        "country": "US",
        "latitude": 35.2974,
        "longitude": -112.1437,
        "total_sites_count": 200,
        "booking_url": "https://koa.com/campgrounds/grand-canyon/",
        "golf_on_site": False,
        "electric_amps": [30, 50],
        "water_hookup": True
    },
    {
        "name": "Banff / Black Forest KOA",
        "provider_network": "koa",
        "external_facility_id": "banff-koa",
        "state_province": "AB",
        "country": "CA",
        "latitude": 51.1784,
        "longitude": -115.5708,
        "total_sites_count": 150,
        "booking_url": "https://koa.com/campgrounds/banff/",
        "golf_on_site": False,
        "electric_amps": [30, 50],
        "water_hookup": True
    },
    {
        "name": "Bar Harbor / Oceanside KOA Holiday",
        "provider_network": "koa",
        "external_facility_id": "bar-harbor-koa",
        "state_province": "ME",
        "country": "US",
        "latitude": 44.4253,
        "longitude": -68.3242,
        "total_sites_count": 180,
        "booking_url": "https://koa.com/campgrounds/bar-harbor-oceanside/",
        "golf_on_site": False,
        "electric_amps": [30, 50],
        "water_hookup": True
    },
    {
        "name": "Yellowstone Park / Mountainside KOA Journey",
        "provider_network": "koa",
        "external_facility_id": "yellowstone-koa",
        "state_province": "MT",
        "country": "US",
        "latitude": 44.6653,
        "longitude": -111.1066,
        "total_sites_count": 220,
        "booking_url": "https://koa.com/campgrounds/yellowstone-park/",
        "golf_on_site": False,
        "electric_amps": [30, 50],
        "water_hookup": True
    }
]

def ingest_private_networks():
    print("[*] Ingesting Private RV & Glamping Resorts...")
    try:
        res = supabase.table("campgrounds").upsert(
            PRIVATE_RESORTS, 
            on_conflict="provider_network,external_facility_id"
        ).execute()
        print(f"[+] Successfully upserted {len(PRIVATE_RESORTS)} private resorts into Supabase.")
    except Exception as e:
        print(f"[!] Database insert error: {e}")

if __name__ == "__main__":
    ingest_private_networks()
