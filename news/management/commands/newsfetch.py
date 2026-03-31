import feedparser
import requests
import io
import re
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import datetime

def html_to_strapi_blocks(html_content):
    """
    Converts a simple HTML string into Strapi Blocks JSON format.
    Strapi Blocks expect a list of objects with type and children.
    """
    if not html_content:
        return []
    
   
    clean_content = re.sub(r'', '', html_content, flags=re.DOTALL)
   
    text_only = re.sub(r'<[^>]*>', '', clean_content).strip()
    
    
    return [
        {
            "type": "paragraph",
            "children": [
                {
                    "type": "text",
                    "text": text_only
                }
            ]
        }
    ]

def clean_drupal_text(html_content, strip_all_tags=False):
    """
    Improved cleaning to specifically target Drupal's persistent comment tags.
    """
    if not html_content:
        return ""
    
    #Correctly target and remove comments
    cleaned_text = re.sub(r'', '', html_content, flags=re.DOTALL)
    
    if strip_all_tags:
        cleaned_text = re.sub(r'<[^>]*>', '', cleaned_text)
        cleaned_text = " ".join(cleaned_text.split()).strip()
    
    return cleaned_text.strip()

class Command(BaseCommand):
    help = 'Syncs news articles, full content, and images from ICPAU to Strapi'

    def handle(self, *args, **options):
        STRAPI_BASE_URL = "http://64.225.121.230:1337" 
        STRAPI_TOKEN = "aaa2621af4b32b5d7c56ad777f99a357b97f1dd138e2e098a35f6acc9667a8529eeb5a7bc6a295078a6a21401adfd7664e06f103990f7c7570224632dfdb22ee15df6ed949c9bf039e0860753b885697685827163bcda8a682947d401d736460e0386cc01db8d0ca8d5f1d1630f9ab3f16878000ee1683e2829b54486f8a9ec6"
        RSS_URL = "https://www.icpau.co.ug/rss.xml" 
        
        headers = {"Authorization": f"Bearer {STRAPI_TOKEN}"}
        
        self.stdout.write("Connecting to ICPAU Feed...")
        feed = feedparser.parse(RSS_URL)

        for entry in feed.entries:
            clean_title = clean_drupal_text(entry.title, strip_all_tags=True)
            raw_html = getattr(entry, 'summary', '')

            #  IMAGE FIX
            image_id = None
            image_url = None

            # 1. Check standard RSS media fields
            if hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
                image_url = entry.enclosures[0].href
            elif 'media_content' in entry:
                image_url = entry.media_content[0]['url']
            
            #  Extract from HTML if the above are null
            if not image_url:
                img_match = re.search(r'<img [^>]*src="([^"]+)"', raw_html)
                if img_match:
                    image_url = img_match.group(1)
                    if image_url.startswith('/'):
                        image_url = "https://www.icpau.co.ug" + image_url

            if image_url:
                try:
                    img_temp = requests.get(image_url, timeout=15)
                    if img_temp.status_code == 200:
                        file_name = f"icpau_{now().strftime('%Y%m%d_%H%M%S')}.jpg"
                        files = {'files': (file_name, io.BytesIO(img_temp.content), 'image/jpeg')}
                        upload_res = requests.post(f"{STRAPI_BASE_URL}/api/upload", headers=headers, files=files)
                        if upload_res.status_code == 200:
                            image_id = upload_res.json()[0]['id']
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Image sync failed: {e}"))

            
            # Convert raw HTML string into Strapi Blocks JSON
            strapi_blocks_content = html_to_strapi_blocks(raw_html)
            plain_description = clean_drupal_text(raw_html, strip_all_tags=True)

            payload = {
                "data": {
                    "title": clean_title,
                    "description": plain_description[:250],
                    "content": strapi_blocks_content,
                    "author": "ICPAU",
                    "featuredImage": [image_id] if image_id else [],
                    "publishDate": datetime(*entry.published_parsed[:3]).strftime('%Y-%m-%d') if hasattr(entry, 'published_parsed') else now().strftime('%Y-%m-%d'),
                    "publishedAt": now().isoformat() 
                }
            }

            post_res = requests.post(f"{STRAPI_BASE_URL}/api/news-articles", json=payload, headers=headers)
            if post_res.status_code == 201:
                self.stdout.write(self.style.SUCCESS(f"Successfully Synced: {clean_title}"))