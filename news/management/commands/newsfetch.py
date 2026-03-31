import feedparser
import requests
import io
from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import datetime

class Command(BaseCommand):
    help = 'Syncs news and images from ICPAU RSS feed to Strapi CMS'

    def handle(self, *args, **options):
        # SETTINGS 
        STRAPI_BASE_URL = "http://64.225.121.230:1337" 
        STRAPI_TOKEN = "aaa2621af4b32b5d7c56ad777f99a357b97f1dd138e2e098a35f6acc9667a8529eeb5a7bc6a295078a6a21401adfd7664e06f103990f7c7570224632dfdb22ee15df6ed949c9bf039e0860753b885697685827163bcda8a682947d401d736460e0386cc01db8d0ca8d5f1d1630f9ab3f16878000ee1683e2829b54486f8a9ec6"
        RSS_URL = "https://www.icpau.co.ug/rss.xml" 
        
        headers = {"Authorization": f"Bearer {STRAPI_TOKEN}"}
        
        self.stdout.write("Fetching feed...")
        feed = feedparser.parse(RSS_URL)

        if not feed.entries:
            self.stdout.write(self.style.ERROR("No entries found. Check if the RSS_URL is correct."))
            return

        for entry in feed.entries:
            #  CHECK FOR DUPLICATES
            
            check_url = f"{STRAPI_BASE_URL}/api/news-articles?filters[title][$eq]={entry.title}"
            try:
                check_res = requests.get(check_url, headers=headers)
                if check_res.status_code == 200 and check_res.json().get('data'):
                    self.stdout.write(f"Skipping: {entry.title} (Already exists)")
                    continue
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Connection error checking duplicates: {e}"))
                continue

            # HANDLE IMAGE UPLOAD
            image_id = None
            image_url = None
            
            if hasattr(entry, 'enclosures') and len(entry.enclosures) > 0:
                image_url = entry.enclosures[0].href
            elif hasattr(entry, 'media_content'):
                image_url = entry.media_content[0]['url']

            if image_url:
                try:
                    img_temp = requests.get(image_url, timeout=10)
                    if img_temp.status_code == 200:
                        files = {
                            'files': (f"icpau_news_{now().strftime('%Y%m%d%H%M%S')}.jpg", io.BytesIO(img_temp.content), 'image/jpeg')
                        }
                        upload_res = requests.post(f"{STRAPI_BASE_URL}/api/upload", headers=headers, files=files)
                        if upload_res.status_code == 200:
                            image_id = upload_res.json()[0]['id']
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"Image upload failed for {entry.title}: {e}"))

            #  EXTRACT AND FORMAT DATE
            
            if hasattr(entry, 'published_parsed'):
                pub_date = datetime(*entry.published_parsed[:3]).strftime('%Y-%m-%d')
            else:
                pub_date = now().strftime('%Y-%m-%d')

            #  PREPARE PAYLOAD
            payload = {
                "data": {
                    "title": entry.title,
                    "description": entry.summary[:250] if hasattr(entry, 'summary') else "",
                    "content": entry.content[0].value if hasattr(entry, 'content') else entry.summary,
                    "author": "ICPAU",
                    "featuredImage": image_id, 
                    "publishDate": pub_date, 
                    "publishedAt":now().isoformat()    
                }
            }

            # PUSH TO STRAPI
            post_res = requests.post(f"{STRAPI_BASE_URL}/api/news-articles", json=payload, headers=headers)
            
            if post_res.status_code == 201:
                self.stdout.write(self.style.SUCCESS(f"Successfully Synced: {entry.title}"))
            else:
                self.stdout.write(self.style.ERROR(f"Failed to save {entry.title}: {post_res.text}"))