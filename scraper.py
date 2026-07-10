import feedparser
from bs4 import BeautifulSoup
import requests
import os
import re

def get_latest_car_news(feed_url="https://www.carscoops.com/feed/"):
    """
    Fetches the latest article from a reliable car news RSS feed.
    Downloads the high-resolution lead image and returns article data.
    """
    print(f"Fetching RSS feed from: {feed_url}")
    feed = feedparser.parse(feed_url)
    
    if not feed.entries:
        raise Exception("No entries found in RSS feed")
        
    for entry in feed.entries:
        # Carscoops puts images in media_content
        image_url = None
        if "media_content" in entry:
            image_url = entry.media_content[0].get("url")
        
        # If not in media_content, try to find an img tag in the summary/content
        if not image_url and "content" in entry:
            soup = BeautifulSoup(entry.content[0].value, 'html.parser')
            img_tag = soup.find('img')
            if img_tag:
                image_url = img_tag.get('src')
        
        if not image_url and "summary" in entry:
            soup = BeautifulSoup(entry.summary, 'html.parser')
            img_tag = soup.find('img')
            if img_tag:
                image_url = img_tag.get('src')
                
        if not image_url:
            continue # skip entries without images
            
        title = entry.title
        link = entry.link
        
        # Get full text by fetching the article URL (basic scraping)
        print(f"Scraping full article text from: {link}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        try:
            resp = requests.get(link, headers=headers)
            soup = BeautifulSoup(resp.content, 'html.parser')
            
            # Carscoops text is usually in paragraphs inside the main article body
            paragraphs = soup.find_all('p')
            article_text = " ".join([p.get_text() for p in paragraphs if len(p.get_text()) > 30])
        except Exception as e:
            print(f"Error scraping full text: {e}")
            article_text = entry.summary # fallback
            
        # Download the image
        os.makedirs("assets", exist_ok=True)
        image_path = os.path.join("assets", "latest_car.jpg")
        
        print(f"Downloading high-res image from: {image_url}")
        img_resp = requests.get(image_url, headers=headers)
        with open(image_path, 'wb') as f:
            f.write(img_resp.content)
            
        return {
            "title": title,
            "url": link,
            "article_text": article_text,
            "image_path": image_path
        }
    
    raise Exception("No valid articles with images found")

if __name__ == "__main__":
    news = get_latest_car_news()
    print("\n--- Scraped News ---")
    print(f"Title: {news['title']}")
    print(f"Text Preview: {news['article_text'][:200]}...")
    print(f"Image Path: {news['image_path']}")
