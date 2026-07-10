import requests
import json
import os
import random

SYSTEM_PROMPT = """You are an expert Azerbaijani automotive journalist writing for a premium Instagram page called @azvscars.
Your job is to pick two real, well-known competing cars and write a detailed comparison post in Azerbaijani.

CRITICAL LANGUAGE RULES:
- Write ONLY correct, natural Azerbaijani. Do NOT invent words.
- Valid Azerbaijani letters: A B C Ç D E Ə F G Ğ H X I İ J K Q L M N O Ö P R S Ş T U Ü V Y Z
- Common Azerbaijani automotive words: GÜC (power), SÜRƏT (speed), QİYMƏT (price), MÜHƏRRİK (engine), DÖYÜŞ (battle), YARIŞI (race/competition), DÖVRÜ (era), XÜLASƏSİ (summary), REYTİNQİ (rating), ZƏFƏRI (victory), RƏQABƏT (competition), ÜSTÜNLÜK (superiority)
- battle_title must be 2-4 words MAX, real Azerbaijani, related to the specific cars. Examples: "ALMAN DÖYÜŞÜ", "SUV YARIŞI", "SEDAN RƏQABƏTI", "İTALYAN ZƏFƏRI", "FRANSIZ DÖYÜŞÜ", "ELEKTRİK YARIŞI"
- battle_title must be 2-4 words MAX, real Azerbaijani, related to the specific cars. Examples: "ALMAN DÖYÜŞÜ", "SUV YARIŞI", "SEDAN RƏQABƏTI", "İTALYAN ZƏFƏRI", "FRANSIZ DÖYÜŞÜ", "ELEKTRİK YARIŞI"

Pick two cars that compete directly (BMW M3 vs Mercedes C63, Toyota Camry vs Honda Accord, Range Rover vs G-Class, Porsche 911 vs Audi R8, Ford Mustang vs Chevy Camaro, etc.).
Vary the pairs every time. Provide ONLY accurate, real-world specs.

Output ONLY valid JSON, absolutely no other text:
{
  "car1_name": "BMW M3 Competition",
  "car2_name": "Mercedes-AMG C63 S",
  "car1_search_query": "BMW M3 G80 side view",
  "car2_search_query": "Mercedes AMG C63 W205 side view",
  "battle_title": "ALMAN DÖYÜŞÜ",
  "slide2_title": "MÜHƏRRİK VƏ GÜC",
  "slide2_car1_stat": "3.0L I6 / 503 HP",
  "slide2_car2_stat": "4.0L V8 / 503 HP",
  "slide3_title": "0-100 KM/S",
  "slide3_car1_stat": "3.8 san.",
  "slide3_car2_stat": "3.9 san.",
  "slide4_title": "BAŞLANĞIC QİYMƏTİ",
  "slide4_car1_stat": "$76,000",
  "slide4_car2_stat": "$83,000",
  "caption": "2-3 sentences in natural Azerbaijani comparing these two cars with emojis.",
  "hashtags": "#azvscars #azerbaijan #avto #baku #masin"
}
"""

def generate_comparison(post_type="main") -> dict:
    """
    Calls Cloudflare Workers AI to generate a random car comparison based on the post format.
    post_type can be: "quick", "main", "war", "night"
    """
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("CF_ACCOUNT_ID", "")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CF_API_TOKEN", "")
    
    if not account_id or not api_token:
        print("⚠️ No Cloudflare credentials found in environment. Using dummy data.")
        return {
          "car1_name": "BMW M3 Competition",
          "car2_name": "Mercedes-AMG C63 S",
          "car1_search_query": "BMW M3 G80 side view",
          "car2_search_query": "Mercedes AMG C63 side view",
          "battle_title": "ALMAN DÖYÜŞÜ",
          "slide2_title": "MÜHƏRRİK VƏ GÜC",
          "slide2_car1_stat": "3.0L I6 / 503 HP",
          "slide2_car2_stat": "4.0L V8 / 503 HP",
          "slide3_title": "0-100 KM/S",
          "slide3_car1_stat": "3.8 san.",
          "slide3_car2_stat": "3.9 san.",
          "slide4_title": "BAŞLANĞIC QİYMƏTİ",
          "slide4_car1_stat": "$76,000",
          "slide4_car2_stat": "$83,000",
          "caption": "İki əfsanəvi alman sedan — M3 kompakt güclə, C63 V8 kütləsiylə cavab verir. 🔥 Sən hansını seçərdin?",
          "hashtags": "#azvscars #azerbaijan #avto #baku #masin"
        }
        
    print("Requesting AI generation from Cloudflare Workers AI...")
    
    # We use Llama 3.1 8B Instruct which is very fast, capable, and has a generous free tier on Cloudflare
    model = "@cf/meta/llama-3.1-8b-instruct"
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    seed = random.randint(1, 100000)
    
    # Customize instructions based on post_type
    if post_type == "quick":
        post_instruction = "POST TYPE: 'Quick Choice'. The caption MUST be short and ask 'Sürmək üçün birini seç: A yoxsa B? Məncə bu seçim çox çətindir 👀'. Cars should be simple, highly recognizable."
    elif post_type == "war":
        post_instruction = "POST TYPE: 'Comment War'. The caption MUST ask '100.000 AZN olsa hansını alardın? Sol yoxsa sağ? Cavabı kommentə yaz. Sabah ən çox seçilən maşını yeni rəqiblə çıxarıram.'. Pick expensive cars around 100k budget."
    elif post_type == "night":
        post_instruction = "POST TYPE: 'Dark Night Battle'. The caption MUST ask 'Gecə Bakıda sürmək üçün hansını seçərdin? 1 sözlə yaz: sol yoxsa sağ?'. Pick aggressive, loud cars (e.g. C63, M5, RS7)."
    else:
        post_instruction = "POST TYPE: 'Real VS Battle'. The caption MUST compare 3 features briefly and ask 'Hansı qalibdir?'. Keep it under 5 bullet points."
    
    prompt_content = f"Generate a new, random car comparison. Random Seed: {seed}.\n{post_instruction}\nReturn ONLY the JSON object, no explanation."
    
    payload = {
        "max_tokens": 1000,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content}
        ]
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        result_data = response.json()
        content = result_data["result"]["response"]
        
        # Cloudflare might automatically parse it as a dict if Llama returns perfect JSON
        if isinstance(content, dict):
            return content
            
        content_text = str(content)
        # Clean up JSON formatting if the model wrapped it in markdown blocks
        if "```json" in content_text:
            content_text = content_text.split("```json")[1].split("```")[0].strip()
        elif "```" in content_text:
            content_text = content_text.split("```")[1].split("```")[0].strip()
            
        return json.loads(content_text)
        
    except Exception as e:
        print(f"Failed to fetch or parse JSON from Cloudflare AI. Error: {e}")
        # Optionally, you can print the raw response if available
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"Raw Response: {response.text}")
        raise e

if __name__ == "__main__":
    print(generate_comparison())
