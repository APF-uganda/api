import feedparser
import requests
import io
import re
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import datetime

def html_to_strapi_blocks(html_content):
    if not html_content: return []
    cleaned_text = re.sub(r'', '', html_content, flags=re.DOTALL)
    text_only = re.sub(r'<[^>]*>', ' ', cleaned_text)
    text_only = " ".join(text_only.split()).strip()
    return [{"type": "paragraph", "children": [{"type": "text", "text": text_only}]}]

def clean_drupal_text(html_content, strip_all_tags=False):
    if not html_content: return ""
    cleaned_text = re.sub(r'', '', html_content, flags=re.DOTALL)
    if strip_all_tags:
        cleaned_text = re.sub(r'<[^>]*>', '', cleaned_text)
        cleaned_text = " ".join(cleaned_text.split()).strip()
    return cleaned_text.strip()

class Command(BaseCommand):
    help = 'Final Sync: Forces image association by debugging the upload response'

    def handle(self, *args, **options):
        STRAPI_BASE_URL = "http://64.225.121.230:1337" 
        STRAPI_TOKEN = "aaa2621af4b32b5d7c56ad777f99a357b97f1dd138e2e098a35f6acc9667a8529eeb5a7bc6a295078a6a21401adfd7664e06f103990f7c7570224632dfdb22ee15df6ed949c9bf039e0860753b885697685827163bcda8a682947d401d736460e0386cc01db8d0ca8d5f1d1630f9ab3f16878000ee1683e2829b54486f8a9ec6"
        headers = {"Authorization": f"Bearer {STRAPI_TOKEN}"}
        
        self.stdout.write(self.style.MIGRATE_HEADING("🚀 Starting ICPAU Sync..."))
        feed = feedparser.parse("https://www.icpau.co.ug/rss.xml")

        for entry in feed.entries:
            clean_title = clean_drupal_text(entry.title, True)
            article_url = getattr(entry, 'link', None)
            
            # DB CHECK
            existing_doc_id = None
            try:
                check_res = requests.get(f"{STRAPI_BASE_URL}/api/news-articles?filters[title][$eq]={clean_title}&populate=*", headers=headers)
                check_data = check_res.json().get('data', [])
                if check_data:
                    existing_doc_id = check_data[0].get('documentId') or check_data[0].get('id')
                    if check_data[0].get('featuredImage'):
                        self.stdout.write(f"✅ Skipping: {clean_title} (Fully synced)")
                        continue
            except: pass

           
            image_url = None
            if article_url:
                try:
                    p = requests.get(article_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
                    
                    match = re.search(r'property=["\']og:image["\'][^>]*content=["\']([^"\']+)["\']', p.text) or \
                            re.search(r'src=["\']([^"\']+/public/articles/[^"\']+)["\']', p.text)
                    
                    if match:
                        image_url = match.group(1).replace('&amp;', '&')
                        if image_url.startswith('/'): image_url = "https://www.icpau.co.ug" + image_url
                        self.stdout.write(f"  🔍 Found URL: {image_url[-40:]}")
                except: pass

            #  UPLOAD 
            image_id = None
            if image_url:
                try:
                    img_res = requests.get(image_url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
                    if img_res.status_code == 200:
                        files = {'files': (f"news_{now().strftime('%M%S')}.jpg", io.BytesIO(img_res.content), 'image/jpeg')}
                        up = requests.post(f"{STRAPI_BASE_URL}/api/upload", headers=headers, files=files)
                        
                        if up.status_code in [200, 201]:
                            res_json = up.json()
                            # Strapi v5 returns a list or an object
                            image_id = res_json[0]['id'] if isinstance(res_json, list) else res_json.get('id')
                            self.stdout.write(self.style.SUCCESS(f"  ✨ ID CAPTURED: {image_id}"))
                        else:
                            self.stdout.write(self.style.ERROR(f"  ❌ Strapi Upload Failed: {up.text}"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  ❌ Image logic error: {e}"))

            # --- 4. FINAL SYNC ---
            summary_html = getattr(entry, 'summary', '')
            payload = {
                "data": {
                    "title": clean_title,
                    "description": clean_drupal_text(summary_html, True)[:250] or clean_title,
                    "content": html_to_strapi_blocks(summary_html),
                    "featuredImage": image_id  
                }
            }

            if existing_doc_id:
                sync_res = requests.put(f"{STRAPI_BASE_URL}/api/news-articles/{existing_doc_id}", json=payload, headers=headers)
            else:
                payload["data"].update({
                    "author": "ICPAU", 
                    "publishedAt": now().isoformat(),
                    "publishDate": datetime(*entry.published_parsed[:3]).strftime('%Y-%m-%d') if hasattr(entry, 'published_parsed') else now().strftime('%Y-%m-%d')
                })
                sync_res = requests.post(f"{STRAPI_BASE_URL}/api/news-articles", json=payload, headers=headers)

            # Verification log
            if sync_res.status_code in [200, 201]:
                final_msg = "Fixed Image" if image_id else "Still No Image (Text Only)"
                color = self.style.SUCCESS if image_id else self.style.WARNING
                self.stdout.write(color(f"DONE: {final_msg} - {clean_title}"))
            else:
                self.stdout.write(self.style.ERROR(f"FAIL: {sync_res.status_code} - {sync_res.text}"))