import os
import re
import time
from datetime import datetime, timezone, date, timedelta
import requests
from bs4 import BeautifulSoup
from supabase import create_client, Client
from twilio.rest import Client as TwilioClient
import mailer

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
twilio = TwilioClient(TWILIO_SID, TWILIO_TOKEN) if (TWILIO_SID and TWILIO_TOKEN) else None

# 4-Tier Dispatch Delay Configuration
TIER_CONFIG = {
    "instant":  {"delay_minutes": 1,  "queue_wait_minutes": 0},
    "priority": {"delay_minutes": 3,  "queue_wait_minutes": 3},
    "standard": {"delay_minutes": 10, "queue_wait_minutes": 10},
    "free":     {"delay_minutes": 30, "queue_wait_minutes": 30},
}

# 11 Major Provider Networks Master Booking Horizons (in days)
PROVIDER_HORIZONS = {
    "bcparks": 90,
    "alberta_parks": 90,
    "ontario_parks": 150,
    "recreation_gov": 180,
    "parks_canada": 180,
    "maritimes": 120,
    "sepaq": 365,
    "campspot": 365,
    "hipcamp": 365,
    "koa": 365,
    "rms_cloud": 365
}

# Key Canadian campgrounds mapped to their real Parks Canada mapIds & short-codes
CANADIAN_RADAR_TARGETS = [
    {"name": "Tunnel Mountain Village I", "short_id": "ca-ab-banff-tunnel-1", "map_id": "-2147483634", "provider": "parks_canada"},
    {"name": "Tunnel Mountain Village II", "short_id": "ca-ab-banff-tunnel", "map_id": "-2147483633", "provider": "parks_canada"},
    {"name": "Two Jack Lakeside", "short_id": "ca-ab-banff-twojack", "map_id": "-2147483567", "provider": "parks_canada"},
    {"name": "Lake Louise Tent", "short_id": "ca-ab-banff-louise", "map_id": "-2147483559", "provider": "parks_canada"},
]

last_radar_sync_time = 0


def to_ca_slug(name: str) -> str:
    """
    Converts a display name like 'Tunnel Mountain Village II'
    into the exact frontend key: 'ca-tunnel-mountain-village-ii'
    """
    clean = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")
    return clean if clean.startswith("ca-") else f"ca-{clean}"


def normalize_phone(phone: str) -> str:
    """Ensure phone number has standard E.164 Canadian/US formatting (+1)."""
    if not phone or "@" in str(phone):
        return ""
    digits = "".join(filter(str.isdigit, str(phone)))
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return phone if str(phone).startswith("+") else f"+{digits}"


def get_user_profile_info(contact: str) -> tuple[str, str, str]:
    """Look up subscription_tier, email, and phone from profiles based on user_contact."""
    tier = "free"
    email = contact if "@" in str(contact) else ""
    phone = normalize_phone(contact) if "@" not in str(contact) else ""

    try:
        res = (
            supabase.table("profiles")
            .select("*")
            .or_(f"contact.eq.{contact},email.eq.{contact}")
            .limit(1)
            .execute()
        )
        if res.data and len(res.data) > 0:
            row = res.data[0]
            tier = (row.get("subscription_tier") or "free").lower()
            if not email and row.get("email"):
                email = row.get("email")
            if not phone and row.get("contact") and "@" not in str(row.get("contact")):
                phone = normalize_phone(row.get("contact"))
    except Exception as err:
        print(f"[!] Error fetching profile for {contact}: {err}")

    if tier not in TIER_CONFIG:
        tier = "free"
    return tier, email, phone


def is_date_within_provider_horizon(provider_network: str, target_date_str: str) -> bool:
    """Validates if a target booking date falls within the network's legal horizon."""
    try:
        target_date = datetime.strptime(str(target_date_str)[:10], "%Y-%m-%d").date()
        max_days = PROVIDER_HORIZONS.get(provider_network, 90)
        max_allowed_date = date.today() + timedelta(days=max_days)
        return target_date <= max_allowed_date
    except Exception as e:
        print(f"[!] Error parsing date {target_date_str}: {e}")
        return True


# ----------------- AVAILABILITY ADAPTERS -----------------

def check_parks_canada_availability(park_id_or_name: str, start_date: str, end_date: str) -> tuple[bool, str]:
    """Uses ZenRows to scrape Parks Canada reservation platform."""
    park_map_dictionary = {
        "Tunnel Mountain Village 1": "-2147483634",
        "Tunnel Mountain Village I": "-2147483634",
        "Tunnel Mountain Village II": "-2147483633",
        "Two Jack Lakeside": "-2147483567",
        "Lake Louise Tent": "-2147483559",
    }
    park_map_id = park_map_dictionary.get(park_id_or_name, park_id_or_name)
    target_url = (
        f"https://reservation.pc.gc.ca/create-booking/results"
        f"?mapId={park_map_id}&searchTabGroupId=0&bookingCategoryId=0"
        f"&startDate={start_date}&endDate={end_date}"
    )

    if not ZENROWS_API_KEY:
        print("[!] ZENROWS_API_KEY is missing! Cannot scrape Parks Canada live.")
        return False, target_url

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
        soup = BeautifulSoup(response.text, "html.parser")
        available_sites = soup.find_all(
            lambda tag: tag.name == "button" and tag.text and "Reserve" in tag.text
        )
        if len(available_sites) > 0:
            return True, target_url
    except Exception as e:
        print(f"[!] Error scraping Parks Canada for {park_id_or_name}: {e}")

    return False, target_url


def check_recgov_availability(park_id_or_name: str, external_facility_id: str, start_date: str) -> tuple[bool, str]:
    """Checks Recreation.gov live monthly availability grid."""
    clean_id = str(external_facility_id or "").replace("ridb-", "").strip()
    booking_url = f"https://www.recreation.gov/camping/campgrounds/{clean_id}"

    if not clean_id or clean_id == "None":
        return False, booking_url

    try:
        dt = datetime.strptime(str(start_date)[:10], "%Y-%m-%d")
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
            target_key = f"{str(start_date)[:10]}T00:00:00Z"
            for site_id, site_data in campsites.items():
                if site_data.get("availabilities", {}).get(target_key) == "Available":
                    return True, booking_url
    except Exception as e:
        print(f"[!] Error checking Recreation.gov for {park_id_or_name} ({clean_id}): {e}")

    return False, booking_url


def check_campspot_availability(park_id_or_name: str, external_facility_id: str, start_date: str, end_date: str) -> tuple[bool, str]:
    """Checks Campspot private network for open RV/cabin inventory."""
    clean_slug = str(external_facility_id or "").replace("campspot-", "").strip()
    booking_url = f"https://www.campspot.com/book/{clean_slug}"

    if not clean_slug or clean_slug == "None":
        return False, booking_url

    url = "https://api.campspot.com/api/v2/campsites/availability"
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
        print(f"[!] Error checking Campspot for {park_id_or_name}: {e}")

    return False, booking_url


def check_campsite_availability(provider: str, park: str, ext_id: str, start: str, end: str) -> tuple[bool, str]:
    """Routes scan to the corresponding provider network adapter."""
    if not is_date_within_provider_horizon(provider, start):
        print(f"[-] Skipping scan for {park}: Start date {start} exceeds {provider} booking horizon.")
        return False, ""

    print(f"[*] Scanning {park} on [{provider}] for {start} to {end}...")

    if provider == "recreation_gov":
        return check_recgov_availability(park, ext_id, start)
    elif provider in ["campspot", "koa", "rms_cloud"]:
        return check_campspot_availability(park, ext_id, start, end)
    else:
        return check_parks_canada_availability(park, start, end)


def record_availability_to_db(campground_name: str, short_id: str, target_date: str, is_open: bool):
    """
    Writes availability to `campground_availability` under BOTH the frontend's
    expected `'ca-' + slug(name)` ID AND the short_id so the calendar always matches.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    status_str = "available" if is_open else "reserved"
    slug_id = to_ca_slug(campground_name)

    ids_to_write = {slug_id}
    if short_id:
        ids_to_write.add(short_id)

    for cid in ids_to_write:
        try:
            existing = (
                supabase.table("campground_availability")
                .select("id")
                .eq("campground_id", cid)
                .eq("availability_date", target_date)
                .limit(1)
                .execute()
            )
            if existing.data:
                supabase.table("campground_availability").update({
                    "status": status_str,
                    "timestamp_scraped": now_iso
                }).eq("id", existing.data[0]["id"]).execute()
            else:
                supabase.table("campground_availability").insert({
                    "campground_id": cid,
                    "unit_id": f"{cid}-site-1",
                    "availability_date": target_date,
                    "status": status_str,
                    "timestamp_scraped": now_iso
                }).execute()
        except Exception as e:
            print(f"[!] DB write error for {cid} on {target_date}: {e}")


# ----------------- LOOP 1: 1-MINUTE SHARED SNIPER SCANNER -----------------

def run_sniper_loop():
    now = datetime.now(timezone.utc)
    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S UTC')}] 🎯 Running 1-Minute Shared Sniper Scan...")

    try:
        response = (
            supabase.table("cancellation_alerts")
            .select("*")
            .or_("status.eq.pending,status.eq.active,status.is.null")
            .execute()
        )
        alerts = response.data or []

        if not alerts:
            print("[-] No active alerts in cancellation_alerts queue.")
            return

        unique_targets = {}
        for alert in alerts:
            park = alert.get("specific_site") or alert.get("park_name")
            raw_contact = alert.get("user_contact")
            if not raw_contact or not park:
                continue

            provider = alert.get("provider_network") or "parks_canada"
            ext_id = str(alert.get("external_facility_id") or "")
            start = str(alert.get("start_date"))[:10]
            end = str(alert.get("end_date") or start)[:10]

            key = (provider, park, ext_id, start, end)
            unique_targets.setdefault(key, []).append(alert)

        for (provider, park, ext_id, start, end), matching_alerts in unique_targets.items():
            is_open, book_url = check_campsite_availability(provider, park, ext_id, start, end)

            # Record live result into campground_availability under both slug and ext_id
            record_availability_to_db(park, ext_id, start, is_open)

            if is_open:
                print(f"[+] DROP FOUND at {park} ({start} to {end})! Queuing notifications by tier...")
                for alert in matching_alerts:
                    alert_id = str(alert.get("id"))
                    raw_contact = alert.get("user_contact")
                    tier, email, phone = get_user_profile_info(raw_contact)

                    delay_mins = TIER_CONFIG[tier]["delay_minutes"]
                    wait_mins = TIER_CONFIG[tier]["queue_wait_minutes"]
                    scheduled_for = (now + timedelta(minutes=wait_mins)).isoformat()

                    try:
                        supabase.table("notification_queue").insert({
                            "alert_id": alert_id,
                            "user_email": email or raw_contact,
                            "phone_number": phone,
                            "user_tier": tier,
                            "delay_minutes": delay_mins,
                            "provider_network": provider,
                            "external_facility_id": ext_id,
                            "campground_id": to_ca_slug(park),
                            "campground_name": park,
                            "site_number": "Available",
                            "check_in": start,
                            "check_out": end,
                            "booking_url": book_url,
                            "scheduled_for": scheduled_for,
                            "status": "pending"
                        }).execute()
                        print(f"    -> Queued {tier.upper()} ({delay_mins}m) for {raw_contact}")
                    except Exception:
                        pass

    except Exception as e:
        print(f"[!] Error in Sniper Loop: {e}")


# ----------------- DISPATCH WORKER (HANDLES 1m / 3m / 10m / 30m QUEUE) -----------------

def process_notification_queue():
    now_iso = datetime.now(timezone.utc).isoformat()
    try:
        due = (
            supabase.table("notification_queue")
            .select("*")
            .eq("status", "pending")
            .lte("scheduled_for", now_iso)
            .execute()
        )
        items = due.data or []

        for item in items:
            tier = item.get("user_tier", "free")
            park = item.get("campground_name")
            provider = item.get("provider_network") or "parks_canada"
            ext_id = item.get("external_facility_id") or ""
            start = str(item.get("check_in"))[:10]
            end = str(item.get("check_out"))[:10]
            book_url = item.get("booking_url")
            phone = item.get("phone_number")
            email = item.get("user_email")
            alert_id = item.get("alert_id")

            if tier != "instant":
                still_open, _ = check_campsite_availability(provider, park, ext_id, start, end)
                if not still_open:
                    supabase.table("notification_queue").update(
                        {"status": "cancelled_already_booked"}
                    ).eq("id", item["id"]).execute()
                    print(f"[-] Site at {park} already snagged before {tier.upper()} ({item['delay_minutes']}m) timer expired.")
                    continue

            if email and "@" in email:
                mailer.send_drop_notification(
                    to_email=email,
                    user_tier=tier,
                    campground_name=park,
                    site_number=item.get("site_number", "Available"),
                    check_in=start,
                    check_out=end,
                    booking_url=book_url
                )

            if phone and (tier == "instant" or not (email and "@" in email)):
                mailer.send_sms_alert(
                    to_phone=phone,
                    campground_name=park,
                    site_number=item.get("site_number", "Available"),
                    check_in=start,
                    check_out=end,
                    booking_url=book_url
                )

            supabase.table("notification_queue").update({"status": "sent"}).eq("id", item["id"]).execute()
            if alert_id:
                supabase.table("cancellation_alerts").update({"status": "completed"}).eq("id", alert_id).execute()

    except Exception as e:
        print(f"[!] Error processing notification queue: {e}")


# ----------------- LOOP 2: 30-MINUTE BROAD RADAR LIVE SCRAPER -----------------

def run_broad_radar_sync():
    """
    Runs every 30 minutes: performs real live checks on flagship Canadian campgrounds
    and writes results under `'ca-' + slug(name)` (e.g., `ca-tunnel-mountain-village-ii`).
    """
    global last_radar_sync_time
    current_time = time.time()
    if current_time - last_radar_sync_time < 1800:  # 30 minutes
        return

    last_radar_sync_time = current_time
    now_iso = datetime.now(timezone.utc).isoformat()
    print(f"\n[{now_iso}] 📡 Running 30-Min Broad Radar Live Scrape...")

    today = date.today()
    for target in CANADIAN_RADAR_TARGETS:
        name = target["name"]
        short_id = target["short_id"]
        map_id = target["map_id"]

        # Check upcoming 7-day window starting tomorrow
        for day_offset in range(1, 8):
            check_in = (today + timedelta(days=day_offset)).isoformat()
            check_out = (today + timedelta(days=day_offset + 1)).isoformat()

            is_open, _ = check_parks_canada_availability(map_id, check_in, check_out)
            record_availability_to_db(name, short_id, check_in, is_open)

    print("[+] 30-Min Broad Radar Live Scrape complete.")


def main():
    print("🚀 BasecampCheck 4-Tier Engine Online (Instant: 1m | Priority: 3m | Standard: 10m | Free: 30m)")
    while True:
        run_sniper_loop()
        process_notification_queue()
        run_broad_radar_sync()
        time.sleep(30)


if __name__ == "__main__":
    main()
