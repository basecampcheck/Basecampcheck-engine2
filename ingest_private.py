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

def fetch_sitemap(url, force_zenrows=False):
    """Fetches sitemap smartly, falling back to ZenRows if blocked."""
    print(f"[*] Fetching: {url}")
    content = None

    # Try direct fetch first for standard sites like KOA and Let's Camp
    if not force_zenrows:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        try:
            res = requests.get(url, headers=headers, timeout=20)
            if res.status_code == 200:
                content = res.content
        except Exception:
            pass

    # Fall back to ZenRows for heavily blocked sites like Campspot
    if not content:
        proxy_url = "https://api.zenrows.com/v1/"
        params = {"apikey": ZENROWS_API_KEY, "url": url, "premium_proxy": "true"}
        try:
            res = requests.get(proxy_url, params=params, timeout=45)
            if res.status_code == 200:
                content = res.content
        except Exception as e:
            print(f"[!] ZenRows failed on {url}: {e}")
            return []

    if not content:
        return []

    urls = []
    try:
        # Strip out any HTML wrappers Cloudflare might inject to get pure XML
        text = content.decode("utf-8", errors="ignore")
        if "<sitemapindex" in text or "<urlset" in text:
            start_idx = text.find("<?xml")
            if start_idx == -1:
                start_idx = text.find("<sitemapindex") if "<sitemapindex" in text else text.find("<urlset")
            text = text[start_idx:]
            
        root = ET.fromstring(text.encode("utf-8"))
        namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        if root.tag.endswith('sitemapindex'):
            for sitemap in root.findall('sm:sitemap/sm:loc', namespace):
                urls.extend(fetch_sitemap(sitemap.text, force_zenrows))
        elif root.tag.endswith('urlset'):
            for url_tag in root.findall('sm:url/sm:loc', namespace):
                urls.append(url_tag.text)
    except Exception as e:
        pass # Skip unparseable sub-maps silently
        
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
    blacklist = ["amenities", "groups", "photos", "blog", "general-information", "site-type", "deals"]
    for url in urls:
        if "/campgrounds/" in url:
            parts = url.split("/campgrounds/")
            if len(parts) > 1:
                clean_path = parts[1].strip("/").split("?")[0]
                segments = [s for s in clean_path.split("/") if s]
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
    print("=== Extracting Campspot, KOA, & Let's Camp ===")
    
    # 1. Campspot (Forces ZenRows because Cloudflare is strict)
    campspot_urls = fetch_sitemap("https://www.campspot.com/sitemap.xml", force_zenrows=True)
    campspot_records = extract_campspot_slugs(campspot_urls)
    print(f"Parsed {len(campspot_records)} valid Campspot resorts.")
    
    # 2. KOA (Attempts direct fetch first)
    koa_urls = fetch_sitemap("https://koa.com/sitemap.xml", force_zenrows=False)
    koa_records = extract_koa_slugs(koa_urls)
    print(f"Parsed {len(koa_records)} valid KOA campgrounds.")
    
    # 3. Let's Camp (Attempts direct fetch first)
    letscamp_urls = fetch_sitemap("https://letscamp.ca/sitemap.xml", force_zenrows=False)
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
            print(f"[!] Database insert error: {e}")

if __name__ == "__main__":
    ingest_master_list()
