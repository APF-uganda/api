import feedparser
import requests
import io
import re
import time
from urllib.parse import urlparse
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

    def _make_absolute_url(self, url, base="https://www.icpau.co.ug"):
        """Normalise relative, protocol-relative, and absolute image URLs."""
        if not url:
            return None
        url = url.strip()
        if url.startswith("//"):
            return "https:" + url
        if not url.startswith("http"):
            return base.rstrip("/") + "/" + url.lstrip("/")
        return url

    def _upload_image_to_strapi(self, image_url, strapi_base_url, headers, bot_headers):
        """
        Download the image from image_url and upload it to Strapi's media library.
        Returns the Strapi media ID on success, or None on failure.
        """
        try:
            img_res = requests.get(image_url, timeout=20, headers=bot_headers)
            if img_res.status_code != 200:
                self.stdout.write(self.style.WARNING(f"  ⚠️ Could not download image ({img_res.status_code}): {image_url}"))
                return None

            # Derive a filename from the URL
            parsed_path = urlparse(image_url).path
            filename = parsed_path.split("/")[-1] or "cover.jpg"
            # Strip query strings from filename
            filename = filename.split("?")[0]

            content_type = img_res.headers.get("Content-Type", "image/jpeg").split(";")[0]

            upload_res = requests.post(
                f"{strapi_base_url}/api/upload",
                headers={"Authorization": headers["Authorization"]},
                files={"files": (filename, io.BytesIO(img_res.content), content_type)},
            )

            if upload_res.status_code in [200, 201]:
                uploaded = upload_res.json()
                # Strapi returns a list when uploading via /api/upload
                media_id = uploaded[0].get("id") if isinstance(uploaded, list) else uploaded.get("id")
                return media_id
            else:
                self.stdout.write(self.style.WARNING(f"  ⚠️ Strapi upload failed ({upload_res.status_code}): {upload_res.text[:200]}"))
                return None

        except Exception as e:
            self.stdout.write(self.style.WARNING(f"  ⚠️ Image upload error: {e}"))
            return None

    def handle(self, *args, **options):
        from django.conf import settings
        STRAPI_BASE_URL = getattr(settings, "STRAPI_BASE_URL", "http://64.225.121.230:1337")
        STRAPI_TOKEN = getattr(settings, "STRAPI_TOKEN", "")
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
                        
                        # Normalise to absolute URL (handles relative, protocol-relative, absolute)
                        image_url = self._make_absolute_url(image_url)
                            
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

            # Upload image to Strapi media library and get the media ID
            cover_image_id = None
            if image_url:
                cover_image_id = self._upload_image_to_strapi(image_url, STRAPI_BASE_URL, headers, BOT_HEADERS)

            payload = {
                "data": {
                    "title": clean_title,
                    "description": clean_desc,
                    "content": blocks,
                    "author": "ICPAU",
                    "publishDate": p_date,
                    "publishedAt": now().isoformat(),
                }
            }

            # Only set coverImage if we successfully uploaded one
            if cover_image_id:
                payload["data"]["coverImage"] = cover_image_id

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
                image_status = "🖼️" if cover_image_id else ("🔗" if image_url else "📄")
                self.stdout.write(status_color(f"✅ Synced: {clean_title[:30]}... | Blocks: {block_count} {image_status}"))
            else:
                self.stdout.write(self.style.ERROR(f"❌ Strapi Error: {res.text}"))