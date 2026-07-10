"""
main.py  —  Local test runner for the pipeline (no web server needed).
Run: python3 main.py
"""
import os, tempfile
from ai_comparison   import generate_comparison
from image_fetcher   import fetch_wikipedia_image
from carousel_renderer import render_carousel

def main():
    print("=" * 44)
    print("🚀  AZVSCARS — LOCAL PIPELINE TEST")
    print("=" * 44)

    # 1. AI generation
    print("\n[1/3] Cloudflare AI ilə müqayisə yaradılır…")
    try:
        data = generate_comparison()
        print(f"✅  {data['car1_name']}  VS  {data['car2_name']}")
    except Exception as e:
        print(f"❌  AI error: {e}"); return

    # 2. Fetch images
    print("\n[2/3] Wikipedia şəkilləri yüklənir…")
    os.makedirs("assets", exist_ok=True)
    try:
        img1 = fetch_wikipedia_image(data["car1_search_query"], "assets/car1_temp.jpg")
        img2 = fetch_wikipedia_image(data["car2_search_query"], "assets/car2_temp.jpg")
        print(f"✅  {img1}")
        print(f"✅  {img2}")
    except Exception as e:
        print(f"❌  Image error: {e}"); return

    # 3. Render
    print("\n[3/3] Karusel render edilir…")
    try:
        out = (f"output/{data['car1_name'].replace(' ', '')}"
               f"_vs_{data['car2_name'].replace(' ', '')}")
        render_carousel(data, img1, img2, out)
        print(f"✅  Saved to: {out}")
    except Exception as e:
        print(f"❌  Render error: {e}"); return

    print("\n" + "=" * 44)
    print("🎉  DONE!\n")
    print("--- CAPTION ---")
    print(data["caption"])
    print(data.get("hashtags", ""))

if __name__ == "__main__":
    main()
