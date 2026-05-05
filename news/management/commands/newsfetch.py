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
    """Surgical conversion: Targets main body and cuts off related news lists."""
    if not html_content or len(str(html_content)) < 50:
        return []
    
    soup = BeautifulSoup(clean_drupal_html(html_content), 'html.parser')
    
   
    for noise in soup.find_all([
        "script", "style", "nav", "footer", "header", "aside", "form", ".region-sidebar-second"
    ]):
        noise.decompose()

    #  CONTENT SEARCH 
    
    content_area = (
        soup.find('div', class_='field--name-body') or 
        soup.find('div', property='schema:text') or
        soup.find('article') or
        soup.find('main')
    )

   
    if content_area:
       
        for heading in content_area.find_all(['h2', 'h3', 'strong']):
            if any(term in heading.get_text() for term in ["Related News", "Latest News", "Recent News"]):
               
                for sibling in heading.find_next_siblings():
                    sibling.decompose()
                heading.decompose()
    
    #  BLOCK CONSTRUCTION
    blocks = []
   
    source = content_area if content_area else soup

    for el in source.find_all(['p', 'h2', 'h3', 'li']):
        text = el.get_text().strip()
        
        # Filter out  noise
        if len(text) > 45 and "Drag" not in text: 
            
            if not re.match(r'^\d{1,2}\s[A-Za-z]{3}\s\d{2}$', text):
                blocks.append({
                    "type": "paragraph",
                    "children": [{"type": "text", "text": text}]
                })
            
    return blocks

class Command(BaseCommand):
    help = 'Final Fail-Safe Sync for ICPAU News with Noise Exclusion'

    def handle(self, *args, **options):
        # Configuration
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
                    time.sleep(2) # Prevent rate limiting
                    res = requests.get(article_url, timeout=30, headers=BOT_HEADERS)
                    if res.status_code == 200:
                        full_page_html = res.text
                        soup = BeautifulSoup(res.text, 'html.parser')
                        
                        # Image Search - Try multiple methods
                        # 1. Try Open Graph image (most reliable)
                        og_img = soup.find("meta", property="og:image")
                        if og_img:
                            image_url = og_img.get("content")
                        
                        # 2. Try Twitter card image
                        if not image_url:
                            twitter_img = soup.find("meta", attrs={"name": "twitter:image"})
                            if twitter_img:
                                image_url = twitter_img.get("content")
                        
                        # 3. Try first article image
                        if not image_url:
                            article_img = soup.find("article")
                            if article_img:
                                img_tag = article_img.find("img")
                                if img_tag:
                                    image_url = img_tag.get("src")
                        
                        # 4. Try any image in content area
                        if not image_url:
                            content_img = soup.find("div", class_="field--name-body")
                            if content_img:
                                img_tag = content_img.find("img")
                                if img_tag:
                                    image_url = img_tag.get("src")
                        
                        # Make sure image URL is absolute
                        if image_url and not image_url.startswith('http'):
                            image_url = f"https://www.icpau.co.ug{image_url}"
                            
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"⚠️ Connection error: {e}"))

            # Build Content Blocks
            blocks = html_to_strapi_blocks(full_page_html if full_page_html else entry.get('summary', ''))

            # Build Description 
            clean_desc = ""
            if blocks:
               
                clean_desc = " ".join([b['children'][0]['text'] for b in blocks[:2]])
                clean_desc = (clean_desc[:247] + "...") if len(clean_desc) > 250 else clean_desc
            else:
                clean_desc = re.sub(r'<[^>]*>', '', entry.get('summary', clean_title))

            payload = {
                "data": {
                    "title": clean_title,
                    "description": clean_desc,
                    "content": blocks,
                    "author": "ICPAU",
                    "publishDate": p_date,
                    "publishedAt": now().isoformat(),
                    "coverImage": image_url  # Add the image URL
                }
            }

            # Strapi update, create
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
                status_color = self.style.SUCCESS if block_count > 2 else self.style.WARNING
                image_status = "🖼️" if image_url else "📄"
                self.stdout.write(status_color(f"✅ Synced: {clean_title[:30]}... | Blocks: {block_count} {image_status}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Strapi Error: {res.text}"))