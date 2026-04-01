import feedparser
import requests
import io
import re
import time
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import datetime
from bs4 import BeautifulSoup



def clean_drupal_html(html_content):
    """Strips HTML comments and excessive whitespace."""
    if not html_content:
        return ""
  
    cleaned = re.sub(r'', '', str(html_content), flags=re.DOTALL)
    return cleaned.strip()

def html_to_strapi_blocks(html_content):
    """Converts HTML to Strapi v5 JSON Blocks using text-density discovery."""
    if not html_content or len(str(html_content)) < 50:
        return []
    
    soup = BeautifulSoup(clean_drupal_html(html_content), 'html.parser')
    
    # clean 
    for noise in soup(["script", "style", "nav", "footer", "header", "aside"]):
        noise.decompose()

    blocks = []
    
    
    potential_bodies = soup.find_all(['div', 'article', 'section'])
    best_element = soup
    max_p = 0
    
    for entry in potential_bodies:
        p_count = len(entry.find_all('p'))
        if p_count > max_p:
            max_p = p_count
            best_element = entry

    # Extract paragraphs from the best element found
    for p in best_element.find_all(['p', 'h2', 'h3', 'li']):
        text = p.get_text().strip()
        if len(text) > 25:
            blocks.append({
                "type": "paragraph",
                "children": [{"type": "text", "text": text}]
            })
            
    return blocks

class Command(BaseCommand):
    help = 'Final Fail-Safe Sync for ICPAU News'

    def handle(self, *args, **options):
        STRAPI_BASE_URL = "http://64.225.121.230:1337" 
        STRAPI_TOKEN = "aaa2621af4b32b5d7c56ad777f99a357b97f1dd138e2e098a35f6acc9667a8529eeb5a7bc6a295078a6a21401adfd7664e06f103990f7c7570224632dfdb22ee15df6ed949c9bf039e0860753b885697685827163bcda8a682947d401d736460e0386cc01db8d0ca8d5f1d1630f9ab3f16878000ee1683e2829b54486f8a9ec6"
        headers = {"Authorization": f"Bearer {STRAPI_TOKEN}"}
        BOT_HEADERS = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }

        self.stdout.write(self.style.MIGRATE_HEADING("Connecting..."))
        feed = feedparser.parse("https://www.icpau.co.ug/rss.xml")

        for entry in feed.entries:
            clean_title = entry.title.strip()
            article_url = getattr(entry, 'link', None)
            p_date = datetime(*entry.published_parsed[:3]).strftime('%Y-%m-%d') if hasattr(entry, 'published_parsed') else now().strftime('%Y-%m-%d')

            full_page_html = ""
            image_url = None
            
            if article_url:
                try:
                    time.sleep(2) # Increased delay 
                    res = requests.get(article_url, timeout=30, headers=BOT_HEADERS)
                    if res.status_code == 200:
                        full_page_html = res.text
                        soup = BeautifulSoup(res.text, 'html.parser')
                        
                        # Image search
                        og_img = soup.find("meta", property="og:image")
                        image_url = og_img.get("content") if og_img else None
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"⚠️ Connection error: {e}"))

            # Build Content Blocks
            blocks = html_to_strapi_blocks(full_page_html if full_page_html else entry.get('summary', ''))

            # Build Description
            clean_desc = ""
            if blocks:
                clean_desc = " ".join([b['children'][0]['text'] for b in blocks[:2]])[:250] + "..."
            else:
                clean_desc = re.sub(r'<[^>]*>', '', entry.get('summary', clean_title))

            payload = {
                "data": {
                    "title": clean_title,
                    "description": clean_desc,
                    "content": blocks,
                    "author": "ICPAU",
                    "publishDate": p_date,
                    "publishedAt": now().isoformat()
                }
            }

            # Strapi Sync
            check = requests.get(f"{STRAPI_BASE_URL}/api/news-articles?filters[title][$eq]={clean_title}", headers=headers)
            results = check.json().get('data', [])
            
            if results:
                doc_id = results[0].get('documentId') or results[0].get('id')
                res = requests.put(f"{STRAPI_BASE_URL}/api/news-articles/{doc_id}", json=payload, headers=headers)
            else:
                res = requests.post(f"{STRAPI_BASE_URL}/api/news-articles", json=payload, headers=headers)

            # FEEDBACK
            block_count = len(blocks)
            if res.status_code in [200, 201]:
                color = self.style.SUCCESS if block_count > 0 else self.style.WARNING
                self.stdout.write(color(f"✅ Synced: {clean_title[:30]}... | Blocks: {block_count}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Error: {res.text}"))