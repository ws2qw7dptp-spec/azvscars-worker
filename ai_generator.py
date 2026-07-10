import anthropic
import json
import os

SYSTEM_PROMPT = """You are the head editor for an elite, high-quality Azerbaijani automotive Instagram page.
Your job is to read raw car news (in English) and produce two things:
1. A highly engaging, informative caption in Azerbaijani.
2. A very punchy, dramatic headline in Azerbaijani (max 10 words).

IMPORTANT HEADLINE RULE:
You MUST enclose exactly 2 to 4 of the most important, dramatic words in asterisks (*) so the rendering engine knows to paint them RED. 
For example: "FERRARİ *NƏHAYƏT* Kİ MEXANİKİ *SÜRƏTLƏR QUTUSUNU* QAYTardı"
Or: "YENİ BMW M5-İN GÜCÜ *HƏR KƏSİ* *ŞOKA SƏLDİ*"

Output MUST be valid JSON in this exact format:
{
  "headline": "THE PUNCHY HEADLINE WITH *ASTERISKS* ON RED WORDS",
  "caption": "The detailed Azerbaijani caption here. Include emojis and spacing.",
  "hashtags": "#auto #azerbaijan #cars #baku #news"
}
"""

def generate_post_content(article_text: str, title: str) -> dict:
    """
    Calls Anthropic Claude to generate the headline and caption based on the article.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # Dummy content for testing if no API key is provided
        return {
            "headline": "BU YENİ *HİPERKARIN* QİYMƏTİ *1.3 MİLYON* DOLLARDIR",
            "caption": "Ətraflı məlumat üçün sola sürüşdürün... Bu yeni hiperkar avtomobil dünyasını lərzəyə salıb.",
            "hashtags": "#cars #azerbaijan #auto"
        }
        
    client = anthropic.Anthropic(api_key=api_key)
    
    prompt_content = f"Title: {title}\n\nArticle: {article_text}"
    
    print("Requesting AI generation from Claude...")
    response = client.messages.create(
        model="claude-3-5-sonnet-20240620",
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt_content}]
    )
    
    content_text = response.content[0].text
    
    # Clean up JSON formatting
    if "```json" in content_text:
        content_text = content_text.split("```json")[1].split("```")[0].strip()
    elif "```" in content_text:
        content_text = content_text.split("```")[1].split("```")[0].strip()
        
    try:
        return json.loads(content_text)
    except Exception as e:
        print(f"Failed to parse JSON from AI: {content_text}")
        raise e

if __name__ == "__main__":
    # Test
    res = generate_post_content("The new Ferrari is amazing and fast.", "New Ferrari Revealed")
    print(res)
