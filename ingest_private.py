import os
import requests
import xml.etree.ElementTree as ET
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing Supabase credentials in Railway.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_sitemap_urls(sitemap_url):
    """Recursively fetches and parses XML sitemaps."""
    print(f"[*] Fetching sitemap: {sitemap_url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    urls = []
    try:
        res = requests.get(sitemap_url, headers=headers, timeout=20)
        if res.status_code != 200:
            return urls
        
        root = ET.fromstring(res.content)
        namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        if root.tag.endswith('sitemapindex'):
            for sitemap in root.findall('sm:sitemap/sm:loc', namespace):
                urls.extend(fetch_sitemap_urls(sitemap.text))
        elif root.tag.endswith('urlset'):
            for url in root.findall('sm:url/sm:loc', namespace):
                urls.append(url.text)
    except Exception as e:
        print(f"[!] Error parsing sitemap {sitemap_url}: {e}")
    return urls

def extract_campspot_slugs(urls):
    records = []
    for url in urls:
        if "/book/" in url:
            slug = url.split("/book/")[-1].strip("/")
            records.append({
                "name": slug.replace("-", " ").title(),
                "provider_network": "campspot",
                "external_facility_id": slug,
                "country": "US",
                "booking_url": url
            })
    return records

def extract_koa_slugs(urls):
    records = []
    for url in urls:
        if "/campgrounds/" in url:
            parts = url.split("/campgrounds/")
            if len(parts) > 1 and parts[1].strip("/"):
                slug = parts[1].strip("/")
                records.append({
                    "name": f"{slug.replace('-', ' ').title()} KOA",
                    "provider_network": "koa",
                    "external_facility_id": slug,
                    "country": "US",
                    "booking_url": url
                })
    return records

def extract_letscamp_slugs(urls):
    """Extracts independent Canadian parks from the Let's Camp network."""
    records = []
    for url in urls:
        if "/camps/" in url:
            slug = url.split("/camps/")[-1].strip("/")
            if slug and "?" not in slug:
                records.append({
                    "name": slug.replace("-", " ").title(),
                    "provider_network": "lets_camp",
                    "external_facility_id": slug,
                    "country": "CA",
                    "booking_url": url
                })
    return records

def ingest_master_list():
    print("=== Starting North American Private Network Extraction ===")
    
    # 1. Campspot (Premier Private Resorts & Glamping)
    campspot_urls = fetch_sitemap_urls("https://www.campspot.com/sitemap.xml")
    campspot_records = extract_campspot_slugs(campspot_urls)
    
    # 2. KOA (Major Franchised RV Parks)
    koa_urls = fetch_sitemap_urls("https://koa.com/sitemap.xml")
    koa_records = extract_koa_slugs(koa_urls)
    
    # 3. Let's Camp (Canadian Independent & Municipal Parks)
    letscamp_urls = fetch_sitemap_urls("https://letscamp.ca/sitemap.xml")
    letscamp_records = extract_letscamp_slugs(letscamp_urls)
    
    all_records = campspot_records + koa_records + letscamp_records
    print(f"\n[*] Extraction Complete: Found {len(all_records)} private locations.")
    
    batch_size = 1000
    for i in range(0, len(all_records), batch_size):
        batch = all_records[i:i + batch_size]
        try:
            supabase.table("campgrounds").upsert(
                batch, 
                on_conflict="provider_network,external_facility_id"
            ).execute()
            print(f"[+] Upserted batch of {len(batch)} resorts to Supabase.")
        except Exception as e:
            print(f"[!] Database insert error on batch {i}: {e}")

if __name__ == "__main__":
    ingest_master_list()
