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

def check_campsite_availability(park_id_or_name: str, start_date: str, end_date: str) -> bool:
    """
    Uses ZenRows to scrape Parks Canada (GoingToCamp), 
    then parses the HTML to look for active 'Reserve' buttons.
    """
    # Dictionary converting user-facing park names into precise Parks Canada Map IDs
    park_map_dictionary = {
        "Tunnel Mountain Village 1": "-2147483634", 
        "Tunnel Mountain Village I": "-2147483634", # Added to support Roman numeral formatting (I vs 1)
        "Two Jack Lakeside": "-2147483567",         # Placeholder ID - update if required
    }
    
    # If a matched name is found in the dictionary, resolve it to its correct map ID. 
    # If a user types the ID directly, use that string. Otherwise, gracefully fall back.
    park_map_id = park_map_dictionary.get(park_id_or_name, park_id_or_name)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Scraping availability for {park_id_or_name} (Map ID: {park_map_id}) from {start_date} to {end_date}...")
    
    # 1. The exact Parks Canada / GoingToCamp URL structure
    target_url = f"https://reservation.pc.gc.ca/create-booking/results?mapId={park_map_id}&searchTabGroupId=0&bookingCategoryId=0&startDate={start_date}&endDate={end_date}"
    
    # 2. Route the request through ZenRows with JS and Premium proxy configurations
    proxy_url = "https://api.zenrows.com/v1/"
    params = {
        "apikey": ZENROWS_API_KEY,
        "url": target_url,
        "js_render": "true",
        "premium_proxy": "true",
        "wait_for": ".mat-button-wrapper" # Ensure Angular/React components have rendered
    }

    try:
        response = requests.get(proxy_url, params=params)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 3. Assess if a reserve option is visible on the page
        available_sites = soup.find_all(lambda tag: tag.name == 'button' and tag.text and 'Reserve' in tag.text)
        
        if len(available_sites) > 0:
            return True
            
    except Exception as e:
        print(f"Error scraping {park_id_or_name}: {e}")

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

            if not raw_contact or not park:
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
