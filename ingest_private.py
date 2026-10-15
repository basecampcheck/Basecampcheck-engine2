import os
import requests
import xml.etree.ElementTree as ET
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
ZENROWS_API_KEY = os.environ.get("ZENROWS_API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, ZENROWS_API_KEY]):
    raise ValueError("Missing Supabase or ZenRows credentials in Railway.")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_sitemap_urls(sitemap_url):
    """Recursively fetches and parses XML sitemaps via ZenRows."""
    print(f"[*] Fetching sitemap via ZenRows: {sitemap_url}")
    
    proxy_url = "https://api.zenrows.com/v1/"
    params = {
        "apikey": ZENROWS_API_KEY,
        "url": sitemap_url,
        "premium_proxy": "true"
    }
    
    urls = []
    try:
        res = requests.get(proxy_url, params=params, timeout=45)
        if res.status_code != 200:
            print(f"[!] ZenRows error {res.status_code} on {sitemap_url}")
            return urls
        
        # Clean potential malformed tokens from raw responses
        content = res.content.decode("utf-8", errors="ignore").encode("utf-8")
        root = ET.fromstring(content)
        namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        if root.tag.endswith('sitemapindex'):
            for sitemap in root.findall('sm:sitemap/sm:loc', namespace):
                urls.extend(fetch_sitemap_urls(sitemap.text))
        elif root.tag.endswith('urlset'):
            for url in root.findall('sm:url/sm:loc', namespace):
                urls.append(url.text)
                
    except Exception as e:
        print(f"[!] Sitemap parse error on {sitemap_url}: {e}")
        
    return urls

def extract_campspot_slugs(urls):
    records = []
    seen = set()
    for url in urls:
        if "/book/" in url:
            slug = url.split("/book/")[-1].strip("/").split("?")[0]
            if slug and slug not in seen and "/" not in slug:
                seen.add(slug)
                records.append({
                    "name": slug.replace("-", " ").title(),
                    "provider_network": "campspot",
                    "external_facility_id": slug,
                    "state_province": "Other",
                    "country": "US",
                    "booking_url": f"https://www.campspot.com/book/{slug}"
                })
    return records

def extract_koa_slugs(urls):
    records = []
    seen = set()
    # Exclude sub-pages, media, and marketing routes
    blacklist = ["amenities", "groups", "photos", "blog", "general-information", "site-type", "deals", "events", "reviews"]
    
    for url in urls:
        if "/campgrounds/" in url:
            parts = url.split("/campgrounds/")
            if len(parts) > 1:
                clean_path = parts[1].strip("/").split("?")[0]
                segments = [s for s in clean_path.split("/") if s]
                
                # A true campground root URL has only 1 segment (e.g., 'banff', 'grand-canyon')
                if len(segments) == 1:
                    slug = segments[0]
                    if slug not in seen and not any(b in slug for b in blacklist):
                        seen.add(slug)
                        records.append({
                            "name": f"{slug.replace('-', ' ').title()} KOA",
                            "provider_network": "koa",
                            "external_facility_id": slug,
                            "state_province": "Other",
                            "country": "US",
                            "booking_url": f"https://koa.com/campgrounds/{slug}/"
                        })
    return records

def extract_letscamp_slugs(urls):
    records = []
    seen = set()
    for url in urls:
        if "/camps/" in url:
            slug = url.split("/camps/")[-1].strip("/").split("?")[0]
            if slug and slug not in seen and "/" not in slug:
                seen.add(slug)
                records.append({
                    "name": slug.replace("-", " ").title(),
                    "provider_network": "lets_camp",
                    "external_facility_id": slug,
                    "state_province": "Other",
                    "country": "CA",
                    "booking_url": f"https://letscamp.ca/camps/{slug}"
                })
    return records

def ingest_master_list():
    print("=== Starting North American Private Network Extraction ===")
    
    print("\n--> Fetching Campspot...")
    campspot_urls = fetch_sitemap_urls("https://www.campspot.com/sitemap.xml")
    campspot_records = extract_campspot_slugs(campspot_urls)
    print(f"Parsed {len(campspot_records)} valid Campspot resorts.")
    
    print("\n--> Fetching KOA...")
    koa_urls = fetch_sitemap_urls("https://koa.com/sitemap.xml")
    koa_records = extract_koa_slugs(koa_urls)
    print(f"Parsed {len(koa_records)} valid KOA campgrounds.")
    
    print("\n--> Fetching Let's Camp...")
    letscamp_urls = fetch_sitemap_urls("https://letscamp.ca/sitemap.xml")
    letscamp_records = extract_letscamp_slugs(letscamp_urls)
    print(f"Parsed {len(letscamp_records)} valid Let's Camp grounds.")
    
    all_records = campspot_records + koa_records + letscamp_records
    print(f"\n[*] Total clean locations ready for database: {len(all_records)}")
    
    batch_size = 500
    for i in range(0, len(all_records), batch_size):
        batch = all_records[i:i + batch_size]
        try:
            supabase.table("campgrounds").upsert(
                batch, 
                on_conflict="provider_network,external_facility_id"
            ).execute()
            print(f"[+] Upserted batch {i // batch_size + 1} ({len(batch)} campgrounds)")
        except Exception as e:
            print(f"[!] Database insert error on batch {i}: {e}")

if __name__ == "__main__":
    ingest_master_list()
