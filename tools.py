import os
import re
 
from dotenv import load_dotenv
from groq import Groq
 
from utils.data_loader import load_listings
 
load_dotenv()
 
 
def _get_groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set. Add it to a .env file in the project root.")
    return Groq(api_key=api_key)
 
 
def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    stopwords = {"a", "the", "under", "for", "in", "and", "or", "i", "am", "looking", "is", "at"}
 
    def normalize_size_tokens(s: str) -> set:
        s = s.lower()
        s = re.sub(r"\(.*?\)", "", s)
        return set(s.split())
 
    all_listings = load_listings()
 
    query_tokens = [
        w for w in re.sub(r"[^\w\s]", "", description.lower()).split()
        if w not in stopwords
    ]
 
    filtered = []
    for listing in all_listings:
        if max_price is not None and listing["price"] > max_price:
            continue
        if size is not None:
            listing_size_tokens = normalize_size_tokens(listing["size"])
            requested_size_tokens = normalize_size_tokens(size)
            if "one" not in listing_size_tokens and not requested_size_tokens & listing_size_tokens:
                continue
        filtered.append(listing)
 
    scored = []
    for listing in filtered:
        full_blob = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
            " ".join(listing["colors"]),
        ]).lower()
        priority_blob = " ".join([
            listing["title"],
            " ".join(listing["style_tags"]),
        ]).lower()
 
        score = 0
        for token in query_tokens:
            if token in priority_blob:
                score += 2
            elif token in full_blob:
                score += 1
 
        if score > 0:
            scored.append((score, listing))
 
    scored.sort(key=lambda x: x[0], reverse=True)
    return [listing for _, listing in scored]
 
 
def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    client = _get_groq_client()
 
    item_desc = (
        f"{new_item['title']} — ${new_item['price']}, "
        f"{new_item['condition']} condition, found on {new_item['platform']}"
    )
 
    if not wardrobe["items"]:
        prompt = f"""A user is considering buying this thrifted item: {item_desc}
 
They haven't shared their wardrobe yet. Give them 1-2 general styling suggestions — what kinds of bottoms, shoes, or layers would pair well with it, and what overall vibe it suits. Be specific and casual, not generic."""
    else:
        wardrobe_text = "\n".join(
            f"- {item['name']} ({item['category']}, colors: {', '.join(item['colors'])})"
            for item in wardrobe["items"]
        )
        prompt = f"""A user is considering buying this thrifted item: {item_desc}
 
Their current wardrobe includes:
{wardrobe_text}
 
Suggest 1-2 complete outfit combinations using the new item and specific named pieces from their wardrobe. Add one sentence of styling detail per outfit (how to tuck, roll, layer, etc.)."""
 
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return (
            f"This {new_item.get('category', 'piece')} pairs well with "
            "neutral basics and classic denim for an effortless everyday look."
        )
 
 
def create_fit_card(outfit: str, new_item: dict) -> str:
    if not outfit or not outfit.strip():
        return "Couldn't write a fit card — no outfit was provided."
 
    client = _get_groq_client()
 
    prompt = f"""Write a 2-4 sentence Instagram/TikTok caption for this thrifted outfit.
 
Item: {new_item['title']}
Price: ${new_item['price']}
Platform: {new_item['platform']}
Outfit: {outfit}
 
Rules:
- Sound like a real person posting an OOTD, not a product description
- Mention the item name, price, and platform once each, naturally
- Capture the specific vibe of the outfit
- Keep it casual, fun, and authentic
- No hashtags"""
 
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=1.2,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return (
            f"snagged this {new_item['title'].lower()} off {new_item['platform']} "
            f"for ${new_item['price']} and it's giving everything 🖤"
        )
 