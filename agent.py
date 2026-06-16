"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Complete tools.py and test each tool in isolation before implementing this file.

Usage (once implemented):
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re
 
from tools import search_listings, suggest_outfit, create_fit_card
 
 
def _new_session(query: str, wardrobe: dict) -> dict:
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }
 
 
def _parse_query(query: str) -> dict:
    max_price = None
    size = None
 
    price_match = re.search(r"\$?(\d+(?:\.\d+)?)\s*(?:dollars?)?", query, re.IGNORECASE)
    if price_match:
        max_price = float(price_match.group(1))
 
    size_match = re.search(
        r"\bsize\s+([SMLX]+\d*|XS|SM|ML|XL|XXL|\d+)\b"
        r"|\b(XS|XL|XXL|SM|ML)\b"
        r"|\bsize\s+(\d+(?:\.\d+)?)\b",
        query,
        re.IGNORECASE,
    )
    if size_match:
        size = next(g for g in size_match.groups() if g is not None)
 
    stopwords = {
        "a", "the", "under", "for", "in", "and", "or", "i", "am",
        "looking", "is", "at", "something", "want", "need", "find",
        "me", "my", "size", "dollars", "dollar",
    }
    cleaned = re.sub(r"\$?\d+(?:\.\d+)?", "", query)
    cleaned = re.sub(r"\bsize\s+\S+", "", cleaned, flags=re.IGNORECASE)
    tokens = [w for w in re.sub(r"[^\w\s]", "", cleaned.lower()).split() if w not in stopwords]
    description = " ".join(tokens)
 
    return {"description": description, "size": size, "max_price": max_price}
 
 
def run_agent(query: str, wardrobe: dict) -> dict:
    session = _new_session(query, wardrobe)
 
    parsed = _parse_query(query)
    session["parsed"] = parsed
 
    results = search_listings(parsed["description"], parsed["size"], parsed["max_price"])
    session["search_results"] = results
 
    if not results:
        hints = []
        if parsed["size"]:
            hints.append("removing the size filter")
        if parsed["max_price"]:
            hints.append(f"raising your budget above ${parsed['max_price']:.0f}")
        hints.append("using broader keywords")
        hint_str = ", or ".join(hints)
        session["error"] = (
            f"No listings matched your search. Try {hint_str} and search again."
        )
        return session
 
    session["selected_item"] = results[0]
 
    session["outfit_suggestion"] = suggest_outfit(results[0], wardrobe)
 
    session["fit_card"] = create_fit_card(session["outfit_suggestion"], results[0])
 
    return session
 
 
if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe
 
    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Found: {session['selected_item']['title']}")
        print(f"\nOutfit: {session['outfit_suggestion']}")
        print(f"\nFit card: {session['fit_card']}")
 
    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )
    print(f"Error message: {session2['error']}")