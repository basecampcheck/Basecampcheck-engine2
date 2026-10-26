import os
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from supabase import create_client, Client
from apscheduler.schedulers.blocking import BlockingScheduler
import mailer

load_dotenv()

# Initialize Supabase Client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("CRITICAL: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY is missing from environment variables.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Exact 4-Tier Configuration
# Sniper Loop runs every 1 minute (60s):
# - instant:  1 min scan, 0 min additional queue delay + SMS
# - priority: 3 min queue delay
# - standard: 10 min queue delay
# - free:     30 min queue delay
TIER_CONFIG = {
    "instant":  {"delay_minutes": 1,  "queue_wait_minutes": 0},
    "priority": {"delay_minutes": 3,  "queue_wait_minutes": 3},
    "standard": {"delay_minutes": 10, "queue_wait_minutes": 10},
    "free":     {"delay_minutes": 30, "queue_wait_minutes": 30},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*"
}


def check_recreation_gov_live(campground_id: str, check_in: str, check_out: str):
    """Checks live availability on Recreation.gov for a specific campground and date window."""
    try:
        start_dt = datetime.strptime(check_in[:10], "%Y-%m-%d")
        end_dt = datetime.strptime(check_out[:10], "%Y-%m-%d")
        month_start = start_dt.strftime("%Y-%m-01T00:00:00.000Z")

        url = f"https://www.recreation.gov/api/camps/availability/campground/{campground_id}/month"
        resp = requests.get(url, params={"start_date": month_start}, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return False, None, None

        data = resp.json()
        campsites = data.get("campsites", {})

        # Generate required nights
        num_nights = max(1, (end_dt - start_dt).days)
        required_dates = [
            (start_dt + timedelta(days=i)).strftime("%Y-%m-%dT00:00:00Z")
            for i in range(num_nights)
        ]

        for site_id, site_info in campsites.items():
            availabilities = site_info.get("availabilities", {})
            if all(availabilities.get(d) == "Available" for d in required_dates):
                site_name = site_info.get("site", site_id)
                booking_url = f"https://www.recreation.gov/camping/campgrounds/{campground_id}"
                return True, f"Site {site_name}", booking_url

        return False, None, None
    except Exception as e:
        print(f"[!] Rec.gov check error for {campground_id}: {e}")
        return False, None, None


def check_single_campground_live(campground_id: str, check_in: str, check_out: str):
    """
    Routes availability checks to US (Recreation.gov) or Canadian park scrapers.
    Returns: (is_available: bool, site_number: str, booking_url: str)
    """
    camp_id_str = str(campground_id).strip()

    # 1. If numeric ID, check Recreation.gov directly
    if camp_id_str.isdigit():
        return check_recreation_gov_live(camp_id_str, check_in, check_out)

    # 2. Otherwise check Supabase availability cache / Canadian scraper results
    try:
        res = (
            supabase.table("campground_availability")
            .select("*")
            .eq("campground_id", camp_id_str)
            .gte("date", check_in[:10])
            .lt("date", check_out[:10])
            .eq("status", "Available")
            .execute()
        )
        rows = res.data or []
        if rows:
            first_row = rows[0]
            site_num = first_row.get("site_number", "Available")
            booking_url = first_row.get("booking_url", "https://reservation.pc.gc.ca")
            return True, str(site_num), booking_url
    except Exception:
        pass

    return False, None, None


# =====================================================================
# LOOP 1: THE 1-MINUTE SNIPER LOOP (Runs every 60 seconds)
# Scans active user alerts and queues notifications by tier
# =====================================================================
def run_sniper_loop():
    now = datetime.now(timezone.utc)
    print(f"[{now.isoformat()}] 🎯 Running 1-Minute Sniper Loop...")
    try:
        response = supabase.table("user_alerts").select("*").eq("is_active", True).execute()
        alerts = response.data or []
        if not alerts:
            print("[-] No active user alerts to scan.")
            return

        # Group alerts by unique (campground_id, check_in, check_out) to avoid duplicate scraping
        unique_targets = {}
        for alert in alerts:
            key = (str(alert["campground_id"]), str(alert["check_in"]), str(alert["check_out"]))
            unique_targets.setdefault(key, []).append(alert)

        for (camp_id, check_in, check_out), matching_alerts in unique_targets.items():
            is_open, site_num, booking_url = check_single_campground_live(camp_id, check_in, check_out)

            if is_open:
                for alert in matching_alerts:
                    tier = str(alert.get("user_tier", "free")).lower()
                    if tier not in TIER_CONFIG:
                        tier = "free"

                    delay_mins = TIER_CONFIG[tier]["delay_minutes"]
                    wait_mins = TIER_CONFIG[tier]["queue_wait_minutes"]
                    scheduled_time = now + timedelta(minutes=wait_mins)

                    try:
                        supabase.table("notification_queue").insert({
                            "alert_id": alert["id"],
                            "user_email": alert["user_email"],
                            "phone_number": alert.get("phone_number"),
                            "user_tier": tier,
                            "delay_minutes": delay_mins,
                            "campground_id": camp_id,
                            "campground_name": alert.get("campground_name", camp_id),
                            "site_number": site_num or "Available",
                            "check_in": check_in,
                            "check_out": check_out,
                            "booking_url": booking_url or "https://basecampcheck.com",
                            "scheduled_for": scheduled_time.isoformat(),
                            "status": "pending"
                        }).execute()
                        print(f"[+] Queued {tier.upper()} alert ({delay_mins}m) for {alert['user_email']}")
                    except Exception:
                        # Duplicate pending alert safely ignored via idx_unique_pending_alert
                        pass

        # Immediately dispatch any 'instant' (0-wait) notifications
        process_notification_queue()

    except Exception as e:
        print(f"[!] Sniper Loop error: {e}")


# =====================================================================
# DISPATCH WORKER (Runs every 30 seconds + right after Sniper scan)
# =====================================================================
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
            # For delayed tiers (priority 3m, standard 10m, free 30m), verify spot wasn't already booked
            if item["user_tier"] != "instant":
                still_open, _, _ = check_single_campground_live(
                    item["campground_id"], str(item["check_in"]), str(item["check_out"])
                )
                if not still_open:
                    supabase.table("notification_queue").update(
                        {"status": "cancelled_already_booked"}
                    ).eq("id", item["id"]).execute()
                    print(f"[-] Spot already booked before {item['user_tier']} ({item['delay_minutes']}m) timer expired.")
                    continue

            # 1. Send Email (All Tiers)
            mailer.send_drop_notification(
                to_email=item["user_email"],
                user_tier=item["user_tier"],
                campground_name=item["campground_name"],
                site_number=item["site_number"],
                check_in=str(item["check_in"]),
                check_out=str(item["check_out"]),
                booking_url=item["booking_url"]
            )

            # 2. Send Instant SMS ('instant' 1-min Tier Only)
            if item["user_tier"] == "instant" and item.get("phone_number"):
                mailer.send_sms_alert(
                    to_phone=item["phone_number"],
                    campground_name=item["campground_name"],
                    site_number=item["site_number"],
                    check_in=str(item["check_in"]),
                    check_out=str(item["check_out"]),
                    booking_url=item["booking_url"]
                )

            # 3. Mark queue item as sent & update last_notified_at on user_alerts
            supabase.table("notification_queue").update({"status": "sent"}).eq("id", item["id"]).execute()
            if item.get("alert_id"):
                supabase.table("user_alerts").update(
                    {"last_notified_at": now_iso}
                ).eq("id", item["alert_id"]).execute()

    except Exception as e:
        print(f"[!] Queue Dispatch error: {e}")


# =====================================================================
# LOOP 2: BROAD RADAR CALENDAR LOOP (Runs every 30 minutes)
# Runs existing bulk scraper if present in repo
# =====================================================================
def run_broad_radar_loop():
    print(f"[{datetime.now(timezone.utc).isoformat()}] 📡 Running 30-Min Broad Radar Calendar Sync...")
    try:
        # Automatically calls your existing main.py or scraper.py bulk function if present
        import importlib
        for module_name in ("scraper", "main", "app"):
            try:
                mod = importlib.import_module(module_name)
                for fn_name in ("run_scraper", "scrape_all", "main", "sync_all"):
                    if hasattr(mod, fn_name):
                        print(f"[+] Executing {module_name}.{fn_name}()...")
                        getattr(mod, fn_name)()
                        return
            except ImportError:
                continue
        print("[i] Broad Radar check complete.")
    except Exception as e:
        print(f"[!] Broad Radar Loop error: {e}")


if __name__ == "__main__":
    print("🚀 Starting BasecampCheck 4-Tier Engine (Instant: 1m | Priority: 3m | Standard: 10m | Free: 30m)...")
    scheduler = BlockingScheduler()

    # 1. Sniper Loop: Polls active alerts every 60 seconds (1 minute)
    scheduler.add_job(run_sniper_loop, "interval", seconds=60, max_instances=1, next_run_time=datetime.now(timezone.utc))

    # 2. Queue Dispatcher: Checks for due 3m / 10m / 30m timers every 30 seconds
    scheduler.add_job(process_notification_queue, "interval", seconds=30, max_instances=1)

    # 3. Broad Radar Loop: Refreshes general website map/calendar every 30 minutes
    scheduler.add_job(run_broad_radar_loop, "interval", minutes=30, max_instances=1, next_run_time=datetime.now(timezone.utc))

    scheduler.start()
