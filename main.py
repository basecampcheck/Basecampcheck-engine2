import os
import time
from datetime import datetime, timezone, date, timedelta
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from twilio.rest import Client as TwilioClient

# Load Environment Variables from Railway
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_PHONE_NUMBER")
ZENROWS_API_KEY = os.environ.get("ZENROWS_API_KEY")
RIDB_API_KEY = os.environ.get("RIDB_API_KEY")

# Initialize Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
twilio = TwilioClient(TWILIO_SID, TWILIO_TOKEN)

# Tier scan interval settings (in seconds)
TIER_INTERVALS = {
    "instant": 60,       # 1 minute
    "priority": 180,     # 3 minutes
    "standard": 600,     # 10 minutes
    "free": 1800         # 30 minutes
}

# 11 Major Provider Networks Master Booking Horizons (in days)
PROVIDER_HORIZONS = {
    "bcparks": 90,           # 3 months max rolling window
    "alberta_parks": 90,     # 3 months standard
    "ontario_parks": 150,    # 5 months rolling window
    "recreation_gov": 180,   # 6 months rolling window
    "parks_canada": 180,     # 6 months rolling window
    "maritimes": 120,        # ~4 months regional provincial cap
    "sepaq": 365,            # Seasonal blocks up to 1 year
    "campspot": 365,         # 12 months for private RV networks
    "hipcamp": 365,          # 12 months for glamping
    "koa": 365,              # 12 months for KOA network
    "rms_cloud": 365         # 12 months for luxury golf/RV resorts
}

# In-memory timestamp tracker: { alert_id: last_scanned_unix_timestamp }
last_scanned_tracker = {}

def normalize_phone(phone: str) -> str:
    """Ensure phone number has standard E.164 Canadian/US formatting (+1)."""
    digits = "".join(filter(str.isdigit, phone))
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return phone if phone.startswith("+") else f"+{digits}"

def get_user_tier(contact: str) -> str:
    """Look up the subscription tier in profiles based on user contact/email."""
    try:
        res = (
            supabase.table("profiles")
            .select("subscription_tier")
            .or_(f"contact.eq.{contact},email.eq.{contact}")
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            return res.data[0].get("subscription_tier", "free") or "free"
    except Exception as err:
        print(f"Error fetching tier for {contact}: {err}")
    return "free"

def is_date_within_provider_horizon(provider_network: str, target_date_str: str) -> bool:
    """Validates if a target booking date falls within the network's legal horizon."""
    try:
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        max_days = PROVIDER_HORIZONS.get(provider_network, 90)
        max_allowed_date = date.today() + timedelta(days=max_days)
        return target_date <= max_allowed_date
    except Exception as e:
        print(f"Error parsing date {target_date_str}: {e}")
        return True

# ----------------- AVAILABILITY ADAPTERS -----------------

def check_parks_canada_availability(park_id_or_name: str, start_date: str, end_date: str) -> tuple[bool, str]:
    """Uses ZenRows to scrape Parks Canada reservation platform."""
    park_map_dictionary = {
        "Tunnel Mountain Village 1": "-2147483634",  
        "Tunnel Mountain Village I": "-2147483634",
        "Two Jack Lakeside": "-2147483567",
    }
    park_map_id = park_map_dictionary.get(park_id_or_name, park_id_or_name)
    target_url = (
        f"https://reservation.pc.gc.ca/create-booking/results"
        f"?mapId={park_map_id}&searchTabGroupId=0&bookingCategoryId=0"
        f"&startDate={start_date}&endDate={end_date}"
    )
    
    proxy_url = "https://api.zenrows.com/v1/"
    params = {
        "apikey": ZENROWS_API_KEY,
        "url": target_url,
        "js_render": "true",
        "premium_proxy": "true",
        "wait_for": ".mat-button-wrapper"
    }

    try:
        response = requests.get(proxy_url, params=params, timeout=45)
        soup = BeautifulSoup(response.text, 'html.parser')
        available_sites = soup.find_all(lambda tag: tag.name == 'button' and tag.text and 'Reserve' in tag.text)
        if len(available_sites) > 0:
            return True, target_url
    except Exception as e:
        print(f"Error scraping Parks Canada for {park_id_or_name}: {e}")

    return False, target_url

def check_recgov_availability(park_id_or_name: str, external_facility_id: str, start_date: str) -> tuple[bool, str]:
    """Checks Recreation.gov live monthly availability grid."""
    clean_id = str(external_facility_id or "").replace("ridb-", "").strip()
    booking_url = f"https://www.recreation.gov/camping/campgrounds/{clean_id}"
    
    if not clean_id or clean_id == "None":
        return False, booking_url

    try:
        dt = datetime.strptime(start_date, "%Y-%m-%d")
        month_start = dt.strftime("%Y-%m-01T00:00:00.000Z")
    except Exception:
        month_start = datetime.now(timezone.utc).strftime("%Y-%m-01T00:00:00.000Z")

    url = f"https://www.recreation.gov/api/camps/availability/campground/{clean_id}/month?start_date={month_start}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code == 200:
            campsites = res.json().get("campsites", {})
            target_key = f"{start_date}T00:00:00Z"
            for site_id, site_data in campsites.items():
                if site_data.get("availabilities", {}).get(target_key) == "Available":
                    return True, booking_url
    except Exception as e:
        print(f"Error checking Recreation.gov for {park_id_or_name} ({clean_id}): {e}")

    return False, booking_url

def check_campspot_availability(park_id_or_name: str, external_facility_id: str, start_date: str, end_date: str) -> tuple[bool, str]:
    """Checks Campspot private network for open RV/cabin inventory."""
    clean_slug = str(external_facility_id or "").replace("campspot-", "").strip()
    booking_url = f"https://www.campspot.com/book/{clean_slug}"
    
    if not clean_slug or clean_slug == "None":
        return False, booking_url

    url = f"https://api.campspot.com/api/v2/campsites/availability"
    payload = {
        "campgroundSlug": clean_slug,
        "checkInDate": start_date,
        "checkOutDate": end_date,
        "party": {"adults": 2, "children": 0}
    }
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=15)
        if res.status_code == 200:
            spots = res.json().get("availableSites", [])
            if len(spots) > 0:
                return True, booking_url
    except Exception as e:
        print(f"Error checking Campspot for {park_id_or_name}: {e}")

    return False, booking_url

def check_campsite_availability(alert: dict) -> tuple[bool, str]:
    """Routes scan to the corresponding provider network adapter."""
    provider = alert.get("provider_network", "parks_canada")
    park = alert.get("specific_site") or alert.get("park_name")
    ext_id = alert.get("external_facility_id")
    start = alert.get("start_date")
    end = alert.get("end_date") or start

    # Enforce booking horizon limit
    if not is_date_within_provider_horizon(provider, start):
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Skipping scan for {park}: Start date {start} exceeds {provider} booking horizon.")
        return False, ""

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scanning {park} on network [{provider}] for {start} to {end}...")

    if provider == "recreation_gov":
        return check_recgov_availability(park, ext_id, start)
    elif provider in ["campspot", "koa", "rms_cloud"]:
        return check_campspot_availability(park, ext_id, start, end)
    else:
        # Default to Parks Canada / provincial web scraping
        return check_parks_canada_availability(park, start, end)

# ----------------- ALERT LOOP -----------------

def process_alerts():
    current_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking active alerts...")
    
    try:
        response = (
            supabase.table("cancellation_alerts")
            .select("*")
            .or_("status.eq.pending,status.eq.active,status.is.null")
            .execute()
        )
        alerts = response.data

        if not alerts:
            print("No active alerts in queue.")
            return

        for alert in alerts:
            alert_id = str(alert.get("id"))
            raw_contact = alert.get("user_contact")
            park = alert.get("specific_site") or alert.get("park_name")
            start = alert.get("start_date")
            end = alert.get("end_date") or start

            if not raw_contact or not park:
                continue

            # Check tier interval policy
            tier = get_user_tier(raw_contact)
            required_interval = TIER_INTERVALS.get(tier, 1800)
            
            last_scanned = last_scanned_tracker.get(alert_id, 0)
            elapsed = current_time - last_scanned

            if elapsed < required_interval:
                continue

            last_scanned_tracker[alert_id] = current_time
            print(f"Executing scan for Alert {alert_id} | Tier: {tier.upper()} (Every {required_interval}s)")

            phone = normalize_phone(raw_contact)
            
            # Check availability with network routing
            is_open, book_url = check_campsite_availability(alert)

            if is_open:
                print(f"Opening found for {park}! Sending SMS to {phone}...")
                message_body = (
                    f"BasecampCheck Alert: A site just opened up at {park} "
                    f"for {start} to {end}! Book immediately: {book_url}"
                )

                try:
                    msg = twilio.messages.create(
                        body=message_body,
                        from_=TWILIO_FROM,
                        to=phone
                    )
                    print(f"SMS delivered. Twilio SID: {msg.sid}")

                    supabase.table("cancellation_alerts").update({
                        "status": "completed"
                    }).eq("id", alert_id).execute()

                    last_scanned_tracker.pop(alert_id, None)

                except Exception as sms_err:
                    print(f"Failed to send SMS for alert {alert_id}: {sms_err}")

    except Exception as e:
        print(f"Error querying Supabase: {e}")

def main():
    print("BasecampCheck Multi-Network Polling Engine Online.")
    while True:
        process_alerts()
        time.sleep(60)

if __name__ == "__main__":
    main()
