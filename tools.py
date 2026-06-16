"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts, sorted by relevance (best match first).
        Returns an empty list if nothing matches — does NOT raise an exception.
    """
    # 1. Load all listings
    listings = load_listings()

    # 2. Filter by max_price and size
    filtered = []
    for listing in listings:
        if max_price is not None and listing["price"] > max_price:
            continue
        if size is not None:
            listing_size = listing.get("size", "").lower()
            if size.lower() not in listing_size:
                continue
        filtered.append(listing)

    # 3. Score each listing by keyword overlap with description
    keywords = description.lower().split()

    def score(listing: dict) -> int:
        searchable = " ".join([
            listing.get("title", ""),
            listing.get("description", ""),
            " ".join(listing.get("style_tags", [])),
        ]).lower()
        return sum(1 for kw in keywords if kw in searchable)

    scored = [(listing, score(listing)) for listing in filtered]

    # 4. Drop listings with a score of 0
    scored = [(listing, s) for listing, s in scored if s > 0]

    # 5. Sort by score descending and return just the dicts
    scored.sort(key=lambda x: x[1], reverse=True)
    return [listing for listing, _ in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.
    """
    client = _get_groq_client()

    item_summary = (
        f"Title: {new_item.get('title', 'Unknown')}\n"
        f"Category: {new_item.get('category', 'Unknown')}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Condition: {new_item.get('condition', 'Unknown')}\n"
        f"Price: ${new_item.get('price', '?')}\n"
        f"Platform: {new_item.get('platform', 'Unknown')}"
    )

    # 1. Check whether wardrobe items is empty
    wardrobe_items = wardrobe.get("items", [])

    if not wardrobe_items:
        # 2. Empty wardrobe: ask for general styling advice
        prompt = (
            f"A user found this secondhand item:\n\n{item_summary}\n\n"
            "Their wardrobe is empty, so suggest general styling advice: "
            "what types of pieces pair well with this item, what vibe or aesthetic "
            "it suits, and how someone might build an outfit around it. "
            "Be specific and practical, not generic."
        )
    else:
        # 3. Non-empty wardrobe: suggest specific combinations
        wardrobe_summary = "\n".join(
            f"- {item.get('name', 'Item')}: {item.get('category', '')}, "
            f"colors: {', '.join(item.get('colors', []))}, "
            f"tags: {', '.join(item.get('style_tags', []))}"
            for item in wardrobe_items
        )
        prompt = (
            f"A user found this secondhand item:\n\n{item_summary}\n\n"
            f"Here is their current wardrobe:\n{wardrobe_summary}\n\n"
            "Suggest 1–2 complete outfits using the new item and specific named "
            "pieces from the wardrobe above. Explain why each combination works "
            "in terms of color, style, and vibe. Be specific — name the actual wardrobe pieces."
        )

    # 4. Call the LLM and return its response
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.
    """
    # 1. Guard against empty or whitespace-only outfit string
    if not outfit or not outfit.strip():
        return (
            "Could not generate a caption: no outfit suggestion was provided. "
            "Try running suggest_outfit first and passing its result here."
        )

    title = new_item.get("title", "this thrifted find")
    price = new_item.get("price", "?")
    platform = new_item.get("platform", "a thrift platform")

    # 2. Build a prompt with item details and the outfit suggestion
    prompt = (
        f"Write a 2–4 sentence Instagram/TikTok caption for this outfit.\n\n"
        f"The thrifted item is: {title}, found on {platform} for ${price}.\n\n"
        f"Outfit context:\n{outfit}\n\n"
        "Guidelines:\n"
        "- Sound casual and authentic, like a real OOTD post\n"
        "- Mention the item name, price, and platform naturally (once each)\n"
        "- Capture the vibe in specific, vivid terms\n"
        "- Do not use hashtags\n"
        "- Each caption should feel fresh and different, not templated"
    )

    # 3. Call the LLM with higher temperature for variety
    client = _get_groq_client()
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
    )
    return response.choices[0].message.content.strip()