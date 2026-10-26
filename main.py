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
    "
