import os
import time
from datetime import datetime, timezone
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

def check_campsite_availability(park_id_or_name: str, start_date: str, end_date: str) -> bool:
    """Uses ZenRows to scrape Parks Canada (GoingToCamp) and checks for active 'Reserve' buttons."""
    park_map_dictionary = {
        "Tunnel Mountain Village 1": "-2147483634", 
        "Tunnel Mountain Village I": "-2147483634",
        "Two Jack Lakeside": "-2147483567",
    }
    
    park_map_id = park_map_dictionary.get(park_id_or_name, park_id_or_name)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scraping {park_id_or_name} (Map ID: {park_map_id}) for {start_date} to {end_date}...")
    
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
            return True
            
    except Exception as e:
        print(f"Error scraping {park_id_or_name}: {e}")

    return False

def process_alerts():
    current_time = time.time()
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking active alerts...")
    
    try:
        # Fetch active alerts (either status is pending, active, or NULL)
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
            end = alert.get("end_date")

            if not raw_contact or not park:
                continue

            # Determine subscription tier & required interval
            tier = get_user_tier(raw_contact)
            required_interval = TIER_INTERVALS.get(tier, 1800)
            
            last_scanned = last_scanned_tracker.get(alert_id, 0)
            elapsed = current_time - last_scanned

            # Skip if this alert is not yet due under its tier policy
            if elapsed < required_interval:
                continue

            # Update scan timestamp
            last_scanned_tracker[alert_id] = current_time
            print(f"Executing scan for Alert {alert_id} | Tier: {tier.upper()} (Every {required_interval}s)")

            phone = normalize_phone(raw_contact)
            
            # Run availability check
            is_open = check_campsite_availability(park, start, end)

            if is_open:
                print(f"Opening found for {park}! Sending SMS to {phone}...")
                message_body = (
                    f"BasecampCheck Alert: A site just opened up at {park} "
                    f"for {start} to {end}! Book immediately: https://reservation.pc.gc.ca/"
                )

                try:
                    msg = twilio.messages.create(
                        body=message_body,
                        from_=TWILIO_FROM,
                        to=phone
                    )
                    print(f"SMS delivered. Twilio SID: {msg.sid}")

                    # Mark alert completed so it doesn't duplicate
                    supabase.table("cancellation_alerts").update({
                        "status": "completed"
                    }).eq("id", alert_id).execute()

                    # Evict from tracker
                    last_scanned_tracker.pop(alert_id, None)

                except Exception as sms_err:
                    print(f"Failed to send SMS for alert {alert_id}: {sms_err}")

    except Exception as e:
        print(f"Error querying Supabase: {e}")

def main():
    print("BasecampCheck Tiered Scraper Engine Online.")
    while True:
        process_alerts()
        # Loop evaluates the queue every 60 seconds to process Instant scans on time
        time.sleep(60)

if __name__ == "__main__":
    main()
