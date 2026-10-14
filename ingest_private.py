import os
import requests
import xml.etree.ElementTree as ET
from supabase import create_client

# Environment variables from Railway
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing Supabase credentials in Railway.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_sitemap_urls(sitemap_url):
    """Recursively fetches and parses XML sitemaps and sitemap indexes."""
    print(f"[*] Fetching sitemap: {sitemap_url}")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    try:
        response = requests.get(sitemap_url, headers=headers, timeout=20)
        if response.status_code != 200:
            print(f"[!] Failed to fetch {sitemap_url} - Status: {response.status_code}")
            return []
        
        root = ET.fromstring(response.content)
        # Sitemaps use a standard namespace
        namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        urls = []
        
        # If it's an index, recursively fetch the sub-sitemaps
        if root.tag.endswith('sitemapindex'):
            for sitemap in root.findall('sm:sitemap/sm:loc', namespace):
                urls.extend(fetch_sitemap_urls(sitemap.text))
        # If it's a URL set, extract the locations
        elif root.tag.endswith('urlset'):
            for url in root.findall('sm:url/sm:loc', namespace):
                urls.append(url.text)
                
        return urls
    except Exception as e:
        print(f"[!] Error parsing sitemap {sitemap_url}: {e}")
        return []

def extract_campspot_slugs(urls):
    """Filters Campspot URLs to only grab valid campground booking pages."""
    records = []
    for url in urls:
        # Example URL: https://www.campspot.com/book/sun-outdoors-rocky-mountains
        if "/book/" in url:
            slug = url.split("/book/")[-1].strip("/")
            # Create a base skeleton record to ingest
            records.append({
                "name": slug.replace("-", " ").title(),
                "provider_network": "campspot",
                "external_facility_id": slug,
                "country": "US", # Base assumption, can be updated later
                "booking_url": url
            })
    return records

def extract_koa_slugs(urls):
    """Filters KOA URLs to only grab valid campground pages."""
    records = []
    for url in urls:
        # Example URL: https://koa.com/campgrounds/banff/
        if "/campgrounds/" in url:
            parts = url.split("/campgrounds/")
            if len(parts) > 1:
                slug = parts[1].strip("/")
                if slug:
                    records.append({
                        "name": f"{slug.replace('-', ' ').title()} KOA",
                        "provider_network": "koa",
                        "external_facility_id": slug,
                        "country": "US",
                        "booking_url": url
                    })
    return records

def ingest_master_list():
    print("=== Starting Private Network Sitemap Extraction ===")
    
    # 1. Process Campspot
    print("\n--> Analyzing Campspot Network...")
    campspot_raw_urls = fetch_sitemap_urls("https://www.campspot.com/sitemap.xml")
    campspot_records = extract_campspot_slugs(campspot_raw_urls)
    
    # 2. Process KOA
    print("\n--> Analyzing KOA Network...")
    koa_raw_urls = fetch_sitemap_urls("https://koa.com/sitemap.xml")
    koa_records = extract_koa_slugs(koa_raw_urls)
    
    all_records = campspot_records + koa_records
    print(f"\n[*] Extraction Complete: Found {len(all_records)} private locations.")
    
    # 3. Batch Insert to Supabase (Chunks of 1000 to avoid payload limits)
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
