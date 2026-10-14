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
    """Recursively fetches and parses XML sitemaps using ZenRows to bypass Cloudflare."""
    print(f"[*] Fetching sitemap via ZenRows: {sitemap_url}")
    
    proxy_url = "https://api.zenrows.com/v1/"
    params = {
        "apikey": ZENROWS_API_KEY,
        "url": sitemap_url,
        "premium_proxy": "true" # Forces residential IPs to bypass Cloudflare
    }
    
    urls = []
    try:
        # Route through ZenRows instead of direct requests
        res = requests.get(proxy_url, params=params, timeout=45)
        
        if res.status_code != 200:
            print(f"[!] ZenRows failed for {sitemap_url} - Status: {res.status_code}")
            return urls
        
        root = ET.fromstring(res.content)
        namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        if root.tag.endswith('sitemapindex'):
            for sitemap in root.findall('sm:sitemap/sm:loc', namespace):
                urls.extend(fetch_sitemap_urls(sitemap.text))
        elif root.tag.endswith('urlset'):
            for url in root.findall('sm:url/sm:loc', namespace):
                urls.append(url.text)
                
    except ET.ParseError as pe:
        print(f"[!] XML Parsing Error on {sitemap_url} (Cloudflare likely still blocking): {pe}")
    except Exception as e:
        print(f"[!] Request Error on {sitemap_url}: {e}")
        
    return urls

# ... (Keep the rest of your extract_campspot_slugs, koa_slugs, etc. functions exactly the same below here)
