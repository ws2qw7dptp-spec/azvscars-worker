import os
import json
import argparse
import requests
import anthropic
import time

# --- Configuration & Environment Setup ---
# Set these environment variables before running the script
AIRTABLE_API_KEY = os.environ.get("AIRTABLE_API_KEY")
AIRTABLE_BASE_ID = os.environ.get("AIRTABLE_BASE_ID")
AIRTABLE_TABLE_NAME = os.environ.get("AIRTABLE_TABLE_NAME", "Cars")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
BANNERBEAR_API_KEY = os.environ.get("BANNERBEAR_API_KEY")
BANNERBEAR_TEMPLATE_ID = os.environ.get("BANNERBEAR_TEMPLATE_ID")

SYSTEM_PROMPT = """You write Instagram content for an Azerbaijani car-market page.
Given structured car data, output JSON with:
- headline: max 8 words, punchy, includes one number if possible
- caption: hook line + 2-3 sentences value + 1 question, in Azerbaijani
- hashtags: 5-8 tags, mix broad and niche
- reel_script: only if format=reel, 3 lines (hook/body/close), Azerbaijani
Never invent data not present in the input. Return ONLY valid JSON."""

def check_env_vars():
    missing = []
    for var in ["AIRTABLE_API_KEY", "AIRTABLE_BASE_ID", "ANTHROPIC_API_KEY", "BANNERBEAR_API_KEY", "BANNERBEAR_TEMPLATE_ID"]:
        if not os.environ.get(var):
            missing.append(var)
    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

def get_ready_records():
    """Fetch rows from Airtable where status='ready'"""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}"
    }
    params = {
        "filterByFormula": "{status} = 'ready'"
    }
    
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    data = response.json()
    return data.get("records", [])

def generate_content(car_row: dict) -> dict:
    """Call Anthropic API to generate captions based on car data"""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(car_row)}]
    )
    
    content_text = response.content[0].text
    
    # Strip markdown block formatting if present
    if content_text.startswith("```json"):
        content_text = content_text.split("```json")[1].split("```")[0].strip()
    elif content_text.startswith("```"):
        content_text = content_text.split("```")[1].split("```")[0].strip()
        
    return json.loads(content_text)

def render_image(car_data: dict, generated_content: dict) -> str:
    """Call Bannerbear API to render the finished image"""
    headers = {
        "Authorization": f"Bearer {BANNERBEAR_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "template": BANNERBEAR_TEMPLATE_ID,
        "modifications": [
            {"name": "headline", "text": generated_content.get("headline", "")},
            {"name": "price", "text": car_data.get("price", "")},
            {"name": "photo", "image_url": car_data.get("photo_url", "")}
        ]
    }
    
    # Start the async render job
    response = requests.post(
        "https://api.bannerbear.com/v2/images",
        headers=headers,
        json=payload
    )
    response.raise_for_status()
    job = response.json()
    
    # For a production script we should poll the API if it's pending
    if job.get("status") == "pending":
        print("  Waiting for Bannerbear to render image...")
        job_id = job.get("uid")
        while True:
            time.sleep(2)
            poll_resp = requests.get(
                f"https://api.bannerbear.com/v2/images/{job_id}",
                headers=headers
            )
            poll_resp.raise_for_status()
            poll_job = poll_resp.json()
            if poll_job.get("status") == "completed":
                return poll_job.get("image_url")
            elif poll_job.get("status") == "failed":
                raise Exception("Bannerbear rendering failed.")
    
    return job.get("image_url")

def update_airtable_record(record_id: str, image_url: str, caption: str, headline: str):
    """Write back the rendered image and mark the record as rendered"""
    url = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}/{AIRTABLE_TABLE_NAME}/{record_id}"
    headers = {
        "Authorization": f"Bearer {AIRTABLE_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "fields": {
            "status": "rendered",
            "rendered_image_url": image_url,
            "generated_caption": caption,
            "generated_headline": headline
        }
    }
    
    response = requests.patch(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def process_record(record, dry_run=False):
    record_id = record["id"]
    fields = record["fields"]
    car_name = fields.get("name", "Unknown Car")
    
    print(f"\nProcessing record: {car_name} (ID: {record_id})")
    
    # Extract only the relevant fields to send to the LLM
    car_data = {
        "name": car_name,
        "price": fields.get("price", ""),
        "specs_json": fields.get("specs_json", "{}"),
        "photo_url": fields.get("photo_url", "")
    }
    
    if not car_data["photo_url"]:
        print(f"  Skipping: No photo_url provided for {car_name}")
        return

    try:
        if dry_run:
            print("  [DRY RUN] Would generate content via Anthropic...")
            gen_content = {
                "headline": f"Amazing {car_name} Deal!",
                "caption": f"Check out this {car_name} for just {car_data['price']}. Is it worth it?",
                "hashtags": "#auto #azerbaijan #cars"
            }
            print("  [DRY RUN] Would render image via Bannerbear...")
            image_url = "https://example.com/dry-run-image.png"
            print("  [DRY RUN] Would update Airtable to status='rendered'...")
        else:
            print("  Generating content via Anthropic...")
            gen_content = generate_content(car_data)
            
            print("  Rendering image via Bannerbear...")
            image_url = render_image(car_data, gen_content)
            
            caption_with_tags = f"{gen_content.get('caption', '')}\n\n{gen_content.get('hashtags', '')}"
            
            print("  Updating Airtable record...")
            update_airtable_record(
                record_id, 
                image_url, 
                caption_with_tags, 
                gen_content.get("headline", "")
            )
            
        print(f"  Successfully processed {car_name}!")
        
    except Exception as e:
        print(f"  ERROR processing {car_name}: {str(e)}")


def main():
    parser = argparse.ArgumentParser(description="Phase 1 Automation: Generate IG posts from Airtable data")
    parser.add_argument("--dry-run", action="store_true", help="Run without making API calls")
    args = parser.parse_args()
    
    try:
        if not args.dry_run:
            check_env_vars()
        else:
            print("Running in DRY RUN mode (no actual API requests will be made).")
            # Set dummy vars just in case
            for var in ["AIRTABLE_API_KEY", "AIRTABLE_BASE_ID", "ANTHROPIC_API_KEY", "BANNERBEAR_API_KEY", "BANNERBEAR_TEMPLATE_ID"]:
                os.environ.setdefault(var, "DUMMY")
    except ValueError as e:
        print(f"Configuration Error: {str(e)}")
        print("Please set these variables in your terminal before running.")
        return

    print("Fetching 'ready' records from Airtable...")
    try:
        if args.dry_run and os.environ.get("AIRTABLE_API_KEY") == "DUMMY":
            records = [{"id": "rec123", "fields": {"name": "Test Car", "price": "15,000 AZN", "photo_url": "http://img.png", "status": "ready"}}]
        else:
            records = get_ready_records()
    except Exception as e:
        print(f"Failed to fetch from Airtable: {str(e)}")
        return
        
    if not records:
        print("No records found with status='ready'.")
        return
        
    print(f"Found {len(records)} record(s) to process.")
    
    for record in records:
        process_record(record, args.dry_run)

if __name__ == "__main__":
    main()
