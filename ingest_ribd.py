import os
import requests
from supabase import create_client

# Reads directly from Railway's environment variables
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
RIDB_API_KEY = os.environ.get("RIDB_API_KEY")

if not all([SUPABASE_URL, SUPABASE_SERVICE_KEY, RIDB_API_KEY]):
    raise ValueError("Missing required environment variables in Railway.")

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

headers = {
    "apikey": RIDB_API_KEY,
    "Accept": "application/json"
}

def ingest_recreation_gov():
    print("[*] Connecting to Recreation.gov (RIDB)...")
    limit = 50
    target_states = ["CA", "NV", "UT", "OR", "FL", "TX", "AZ", "CO"]

    for state in target_states:
        print(f"\n--- Fetching Campgrounds for {state} ---")
        offset = 0
        while True:
            # activity_id=9 filters for Camping
            url = f"https://ridb.recreation.gov/api/v1/facilities?state={state}&activity_id=9&limit={limit}&offset={offset}"
            try:
                res = requests.get(url, headers=headers, timeout=25)
            except Exception as e:
                print(f"[!] Request error: {e}")
                break

            if res.status_code != 200:
                print(f"[!] RIDB Error {res.status_code}: {res.text}")
                break
                
            data = res.json().get("RECDATA", [])
            if not data:
                print(f"Finished pulling {state}.")
                break

            records = []
            for fac in data:
                lat = fac.get("FacilityLatitude")
                lon = fac.get("FacilityLongitude")
                if lat and lon and lat != 0 and lon != 0:
                    records.append({
                        "name": fac.get("FacilityName"),
                        "provider_network": "recreation_gov",
                        "external_facility_id": f"ridb-{fac.get('FacilityID')}",
                        "state_province": state,
                        "country": "US",
                        "latitude": round(float(lat), 6),
                        "longitude": round(float(lon), 6),
                        "total_sites_count": 50,
                        "booking_url": f"https://www.recreation.gov/camping/campgrounds/{fac.get('FacilityID')}",
                        "golf_on_site": False,
                        "electric_amps": [30, 50],
                        "water_hookup": True
                    })

            if records:
                try:
                    supabase.table("campgrounds").upsert(
                        records, 
                        on_conflict="provider_network,external_facility_id"
                    ).execute()
                    print(f"Upserted {len(records)} campgrounds in {state} (offset {offset})")
                except Exception as db_err:
                    print(f"[!] Database insert error: {db_err}")

            offset += limit
            if offset >= 300:  # Pull up to 300 per state
                break

if __name__ == "__main__":
    ingest_recreation_gov()
