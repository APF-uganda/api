import feedparser
import requests
import io
import re
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import datetime

def clean_drupal_text(html_content, strip_all_tags=False):
    """
    Cleans out Drupal debug comments and template suggestions.
    """
    if not html_content:
        return ""
    
    cleaned_text = re.sub(r'', '', html_content, flags=re.DOTALL)
    
    if strip_all_tags:
      
        cleaned_text = re.sub(r'<[^>]*>', '', cleaned_text)
       
        cleaned_text = " ".join(cleaned_text.split()).strip()
    
    return cleaned_text.strip()

class Command(BaseCommand):
    help = 'Syncs news articles, full content, and images from ICPAU to Strapi'

    def handle(self, *args, **options):
        # --- CONFIGURATION ---
        STRAPI_BASE_URL = "http://64.225.121.230:1337" 
        STRAPI_TOKEN = "aaa2621af4b32b5d7c56ad777f99a357b97f1dd138e2e098a35f6acc9667a8529eeb5a7bc6a295078a6a21401adfd7664e06f103990f7c7570224632dfdb22ee15df6ed949c9bf039e0860753b885697685827163bcda8a682947d401d736460e0386cc01db8d0ca8d5f1d1630f9ab3f16878000ee1683e2829b54486f8a9ec6"
        RSS_URL = "https://www.icpau.co.ug/rss.xml" 
        
        headers = {"Authorization": f"Bearer {STRAPI_TOKEN}"}
        
        self.stdout.write("Connecting to ICPAU Feed...")
        feed = feedparser.parse(RSS_URL)

        if not feed.entries:
            self.stdout.write(self.style.ERROR("No news entries found."))
            return

        for entry in feed.entries:
            #  CLEAN TITLE
            clean_title = clean_drupal_text(entry.title, strip_all_tags=True)

            #  CHECK FOR DUPLICATES
            check_url = f"{STRAPI_BASE_URL}/api/news-articles?filters[title][$eq]={clean_title}"
            try:
                check_res = requests.get(check_url, headers=headers)
                if check_res.status_code == 200 and check_res.json().get('data'):
                    self.stdout.write(f"Skipping: {clean_title} (Already exists)")
                    continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Duplicate check failed: {e}"))
                continue

            # HANDLE IMAGES
            image_id = None
            image_url = None
            if hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
                image_url = entry.enclosures[0].href
            elif 'media_content' in entry:
                image_url = entry.media_content[0]['url']

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
                    self.stdout.write(self.style.WARNING(f"Image sync failed for {clean_title}: {e}"))

            #  CONTENT MAPPING
            
            raw_html = getattr(entry, 'summary', '')
            
            # Content keeps HTML tags for 'Read More'
            rich_content = clean_drupal_text(raw_html, strip_all_tags=False)
          
            plain_description = clean_drupal_text(raw_html, strip_all_tags=True)

            #  PREPARE PAYLOAD
            payload = {
                "data": {
                    "title": clean_title,
                    "description": plain_description[:250],
                    "content": rich_content, 
                    "author": "ICPAU",
                    # Use an array [image_id] for Multiple Media fields
                    "featuredImage": [image_id] if image_id else [],
                    "publishDate": datetime(*entry.published_parsed[:3]).strftime('%Y-%m-%d') if hasattr(entry, 'published_parsed') else now().strftime('%Y-%m-%d'),
                    "publishedAt": now().isoformat() 
                }
            }

            # SEND TO STRAPI
            post_res = requests.post(f"{STRAPI_BASE_URL}/api/news-articles", json=payload, headers=headers)
            
            if post_res.status_code == 201:
                self.stdout.write(self.style.SUCCESS(f"Successfully Synced: {clean_title}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to sync {clean_title}: {post_res.text}"))