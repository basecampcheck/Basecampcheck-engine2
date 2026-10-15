import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing Supabase credentials in Railway.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

ACTIVITY_STAYS = [
    # === ALBERTA & BC (Ski, Mountain Adventure & Provincial Badlands) ===
    {
        "name": "Mount Kidd RV Park",
        "provider_network": "independent",
        "external_facility_id": "mount-kidd-kananaskis",
        "state_province": "AB",
        "country": "CA",
        "latitude": 50.8493,
        "longitude": -115.1492,
        "booking_url": "https://www.mountkiddrv.com/",
        "golf_on_site": False
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
        "golf_on_site": False
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
        "golf_on_site": True
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
        "golf_on_site": False
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
        "golf_on_site": False
    },

    # === CALIFORNIA (Golf, Fishing & Stargazing) ===
    {
        "name": "The Springs at Borrego RV Resort & Golf",
        "provider_network": "independent",
        "external_facility_id": "springs-at-borrego-ca",
        "state_province": "CA",
        "country": "US",
        "latitude": 33.2656,
        "longitude": -116.3422,
        "booking_url": "https://www.springsatborrego.com/",
        "golf_on_site": True
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
        "golf_on_site": True
    },
    {
        "name": "The Lakes RV & Golf Resort",
        "provider_network": "independent",
        "external_facility_id": "lakes-rv-chowchilla-ca",
        "state_province": "CA",
        "country": "US",
        "latitude": 37.1147,
        "longitude": -120.2458,
        "booking_url": "https://thelakesrv.com/",
        "golf_on_site": True
    },
    {
        "name": "Rio Bend RV & Golf Resort",
        "provider_network": "independent",
        "external_facility_id": "rio-bend-el-centro-ca",
        "state_province": "CA",
        "country": "US",
        "latitude": 32.7876,
        "longitude": -115.6888,
        "booking_url": "https://www.riobendrvgolfresort.com/",
        "golf_on_site": True
    },
    {
        "name": "Camp Edison Huntington Lake",
        "provider_network": "independent",
        "external_facility_id": "camp-edison-ca",
        "state_province": "CA",
        "country": "US",
        "latitude": 37.2341,
        "longitude": -119.2223,
        "booking_url": "https://www.sce.com/campedison",
        "golf_on_site": False
    },
    {
        "name": "The Sands RV & Golf Resort",
        "provider_network": "independent",
        "external_facility_id": "sands-rv-desert-hot-springs",
        "state_province": "CA",
        "country": "US",
        "latitude": 33.9312,
        "longitude": -116.5186,
        "booking_url": "https://cal-am.com/resorts/the-sands/",
        "golf_on_site": True
    },

    # === COLORADO (Ski Basecamps & Winter Hubs) ===
    {
        "name": "Tiger Run Resort",
        "provider_network": "independent",
        "external_facility_id": "tiger-run-breckenridge",
        "state_province": "CO",
        "country": "US",
        "latitude": 39.5186,
        "longitude": -106.0461,
        "booking_url": "http://www.tigerrunresort.com/",
        "golf_on_site": False
    },
    {
        "name": "Sun Outdoors Rocky Mountains",
        "provider_network": "campspot",
        "external_facility_id": "sun-outdoors-rocky-mountains",
        "state_province": "CO",
        "country": "US",
        "latitude": 40.0886,
        "longitude": -105.9556,
        "booking_url": "https://www.sunoutdoors.com/colorado/sun-outdoors-rocky-mountains",
        "golf_on_site": False
    },
    {
        "name": "Steamboat Springs KOA Holiday",
        "provider_network": "koa",
        "external_facility_id": "steamboat-springs",
        "state_province": "CO",
        "country": "US",
        "latitude": 40.5058,
        "longitude": -106.8778,
        "booking_url": "https://koa.com/campgrounds/steamboat-springs/",
        "golf_on_site": False
    },
    {
        "name": "Crested Butte RV Park",
        "provider_network": "independent",
        "external_facility_id": "crested-butte-rv",
        "state_province": "CO",
        "country": "US",
        "latitude": 38.8697,
        "longitude": -106.9878,
        "booking_url": "https://www.crestedbuttervpark.com/",
        "golf_on_site": False
    },
    {
        "name": "River Dance RV Resort",
        "provider_network": "independent",
        "external_facility_id": "river-dance-gypsum-co",
        "state_province": "CO",
        "country": "US",
        "latitude": 39.6455,
        "longitude": -106.9531,
        "booking_url": "https://www.riverdancervresort.com/",
        "golf_on_site": False
    },

    # === US REGIONAL GEMS (Boating, Off-Road & Coastal) ===
    {
        "name": "Moab Valley RV Resort",
        "provider_network": "campspot",
        "external_facility_id": "moab-valley-rv-resort",
        "state_province": "UT",
        "country": "US",
        "latitude": 38.5956,
        "longitude": -109.5758,
        "booking_url": "https://sunoutdoors.com/utah/moab-valley-rv-resort-campground",
        "golf_on_site": False
    },
    {
        "name": "Camp Gulf RV Resort",
        "provider_network": "independent",
        "external_facility_id": "camp-gulf-destin-fl",
        "state_province": "FL",
        "country": "US",
        "latitude": 30.3792,
        "longitude": -86.3688,
        "booking_url": "https://campgulf.com/",
        "golf_on_site": False
    },
    {
        "name": "Boyne Mountain RV Resort",
        "provider_network": "independent",
        "external_facility_id": "boyne-mountain-mi",
        "state_province": "MI",
        "country": "US",
        "latitude": 45.1633,
        "longitude": -84.9317,
        "booking_url": "https://www.boynemountain.com/",
        "golf_on_site": True
    },
    {
        "name": "Polson Motorcoach Resort",
        "provider_network": "independent",
        "external_facility_id": "polson-motorcoach-mt",
        "state_province": "MT",
        "country": "US",
        "latitude": 47.6749,
        "longitude": -114.1506,
        "booking_url": "https://polsonrvresort.com/",
        "golf_on_site": False
    }
]

def ingest_activities():
    print(f"[*] Ingesting {len(ACTIVITY_STAYS)} activity & sport destinations...")
    try:
        supabase.table("campgrounds").upsert(
            ACTIVITY_STAYS, 
            on_conflict="provider_network,external_facility_id"
        ).execute()
        print(f"[+] Successfully upserted {len(ACTIVITY_STAYS)} activity destinations into Supabase.")
    except Exception as e:
        print(f"[!] Database insert error: {e}")

if __name__ == "__main__":
    ingest_activities()
