import os
import time
from datetime import datetime
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
    Uses ZenRows to scrape the target site without getting blocked, 
    then parses the HTML to look for availability.
    """
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scraping availability for {park} from {start_date} to {end_date}...")
    
    # 1. Build the exact URL for the park you want to check.
    # Note: Adjust this URL structure to match Parks Canada or Alberta Parks search formats
    target_url = f"https://reservation.pc.gc.ca/search?park={park}&start={start_date}&end={end_date}"
    
    # 2. Route the request through ZenRows with premium proxy and JS rendering enabled
    proxy_url = "https://api.zenrows.com/v1/"
    params = {
        "apikey": ZENROWS_API_KEY,
        "url": target_url,
        "js_render": "true",
        "premium_proxy": "true",
    }

    try:
        response = requests.get(proxy_url, params=params)
        
        # 3. Read the HTML returned by ZenRows
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 4. Check for availability keywords or buttons.
        # Note: You will need to inspect the target website to find the exact HTML class name they use.
        available_campsites = soup.find_all(class_='available-site-button-class') 
        
        if len(available_campsites) > 0:
            return True
            
    except Exception as e:
        print(f"Error scraping {park}: {e}")

    return False

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

                    # Mark status as completed so we don't duplicate
                    supabase.table("cancellation_alerts").update({
                        "status": "completed"
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
