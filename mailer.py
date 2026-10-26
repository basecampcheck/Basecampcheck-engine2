import os
import resend
from twilio.rest import Client
from dotenv import load_dotenv

load_dotenv()

# Resend Email Configuration
resend.api_key = os.environ.get("RESEND_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "BasecampCheck <alerts@basecampcheck.com>")

# Twilio SMS Configuration
TWILIO_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_FROM = os.environ.get("TWILIO_PHONE_NUMBER")


def send_sms_alert(
    to_phone: str,
    campground_name: str,
    site_number: str,
    check_in: str,
    check_out: str,
    booking_url: str
):
    """Dispatches 1-minute Instant SMS to Top-Tier ('instant') subscribers via Twilio."""
    if not all([TWILIO_SID, TWILIO_TOKEN, TWILIO_FROM, to_phone]):
        print("[!] Twilio credentials or recipient phone missing. Skipping SMS.")
        return None
    try:
        client = Client(TWILIO_SID, TWILIO_TOKEN)
        body = (
            f"🏕️ BASECAMP DROP: {campground_name} (Site: {site_number}) just opened for "
            f"{check_in} to {check_out}! Book now: {booking_url}"
        )
        msg = client.messages.create(body=body, from_=TWILIO_FROM, to=to_phone)
        print(f"[+] SMS dispatched to {to_phone}: {msg.sid}")
        return msg.sid
    except Exception as e:
        print(f"[!] Twilio SMS failed: {e}")
        return None


def send_drop_notification(
    to_email: str,
    user_tier: str,
    campground_name: str,
    site_number: str,
    check_in: str,
    check_out: str,
    booking_url: str
):
    """Dispatches HTML email drop alert via Resend to all tiers."""
    if not resend.api_key:
        print("[!] RESEND_API_KEY missing. Skipping email.")
        return None

    tier_badge = user_tier.upper()
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 8px; background-color: #ffffff;">
        <div style="margin-bottom: 12px;">
            <span style="background-color: #0f172a; color: #f8fafc; font-size: 11px; font-weight: bold; padding: 4px 8px; border-radius: 4px; letter-spacing: 0.5px;">
                {tier_badge} TIER ALERT
            </span>
        </div>
        <h2 style="color: #0f172a; margin-top: 0;">Campsite Drop Found! 🏕️</h2>
        <p style="color: #334155; font-size: 15px;">
            A campsite matching your alert criteria just became available:
        </p>
        <div style="background-color: #f8fafc; padding: 16px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #ea580c;">
            <p style="margin: 6px 0; color: #0f172a;"><strong>Campground:</strong> {campground_name}</p>
            <p style="margin: 6px 0; color: #0f172a;"><strong>Site:</strong> {site_number}</p>
            <p style="margin: 6px 0; color: #0f172a;"><strong>Dates:</strong> {check_in} to {check_out}</p>
        </div>
        <p style="margin: 24px 0;">
            <a href="{booking_url}" style="background-color: #ea580c; color: #ffffff; padding: 14px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">
                Book on Official Site Now →
            </a>
        </p>
        <p style="font-size: 12px; color: #64748b; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 12px;">
            Campsites sell out quickly. Click above to go directly to the official park reservation portal.
            <br>Sent by BasecampCheck • <a href="https://basecampcheck.com" style="color: #64748b;">Manage Alerts</a>
        </p>
    </div>
    """
    try:
        response = resend.Emails.send({
            "from": SENDER_EMAIL,
            "to": [to_email],
            "subject": f"🏕️ Drop Alert: {campground_name} ({check_in})",
            "html": html_content
        })
        print(f"[+] Email dispatched to {to_email} ({tier_badge})")
        return response
    except Exception as e:
        print(f"[!] Resend error: {e}")
        return None
