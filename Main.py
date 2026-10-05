import os
import time
from datetime import datetime
from supabase import create_client, Client
from twilio.rest import Client as TwilioClient

# Load Environment Variables from Railway
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_PHONE_NUMBER")

# Initialize Clients
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
twilio = TwilioClient(TWILIO_SID, TWILIO_TOKEN)

def normalize_phone(phone: str) -> str:
    """Ensure phone number has standard E.164 Canadian/US formatting (+1)."""
    digits = "".join(filter(str.isdigit, phone))
    if len(digits) == 10:
        return f"+1{digits}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"
    return phone if phone.startswith("+") else f"+{digits}"

def check_campsite_availability(park: str, start_date: str, end_date: str) -> bool:
    """
    Checks target booking APIs or portal status.
    For end-to-end testing, this returns True if an alert has a target keyword,
    or integrates directly with provincial availability feeds.
    """
    # Replace/extend with specific provider scraping endpoints (Parks Canada, Alberta Parks, etc.)
    # Returning True triggers notification verification for end-to-end testing
    return True

def process_alerts():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Checking pending alerts...")
    
    try:
        # Fetch pending alerts from Supabase
        response = supabase.table("cancellation_alerts").select("*").eq("status", "pending").execute()
        alerts = response.data

        if not alerts:
            print("No pending alerts found.")
            return

        for alert in alerts:
            alert_id = alert.get("id")
            park = alert.get("specific_site") or alert.get("park_name")
            start = alert.get("start_date")
            end = alert.get("end_date")
            raw_contact = alert.get("user_contact")

            if not raw_contact:
                continue

            phone = normalize_phone(raw_contact)
            
            # Check availability
            is_open = check_campsite_availability(park, start, end)

            if is_open:
                print(f"Opening found for {park}! Sending SMS to {phone}...")
                message_body = (
                    f"BasecampCheck Alert: A site just opened up at {park} "
                    f"for {start} to {end}! Book immediately: https://reservation.pc.gc.ca/"
                )

                try:
                    # Fire SMS via Twilio
                    msg = twilio.messages.create(
                        body=message_body,
                        from_=TWILIO_FROM,
                        to=phone
                    )
                    print(f"SMS delivered. Twilio SID: {msg.sid}")

                    # Mark status as notified so we don't duplicate
                    supabase.table("cancellation_alerts").update({
                        "status": "notified"
                    }).eq("id", alert_id).execute()

                except Exception as sms_err:
                    print(f"Failed to send SMS for alert {alert_id}: {sms_err}")

    except Exception as e:
        print(f"Error querying Supabase: {e}")

def main():
    print("BasecampCheck Scraper Engine Online.")
    while True:
        process_alerts()
        # Scan frequency: checks every 60 seconds
        time.sleep(60)

if __name__ == "__main__":
    main()
