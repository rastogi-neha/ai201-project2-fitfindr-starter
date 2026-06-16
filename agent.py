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


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """
    Initialize and return a fresh session dict for one user interaction.

    The session dict is the single source of truth for everything that happens
    during a run — it stores the original query, parsed parameters, tool results,
    and any error that caused early termination.
    """
    return {
        "query": query,              # original user query
        "parsed": {},                # extracted description / size / max_price
        "search_results": [],        # list of matching listing dicts
        "selected_item": None,       # top result, passed into suggest_outfit
        "wardrobe": wardrobe,        # user's wardrobe dict
        "outfit_suggestion": None,   # string returned by suggest_outfit
        "fit_card": None,            # string returned by create_fit_card
        "error": None,               # set if the interaction ended early
    }


# ── query parser ──────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract description, size, and max_price from a natural language query
    using regex patterns.

    Examples handled:
        "vintage graphic tee under $30, size M"
        "looking for a jacket under $50 in size L"
        "baggy jeans size XL for less than $40"

    Returns a dict with keys:
        description (str): cleaned query text with price/size fragments removed
        size (str | None): e.g. "M", "XL", "S/M" — None if not found
        max_price (float | None): e.g. 30.0 — None if not found
    """
    # Extract max_price — matches "$30", "under $30", "less than $40", "for $25"
    price_match = re.search(
        r'(?:under|less\s+than|for|max|below|up\s+to)?\s*\$(\d+(?:\.\d+)?)',
        query,
        re.IGNORECASE,
    )
    max_price = float(price_match.group(1)) if price_match else None

    # Extract size — matches "size M", "size XL", "in a M", standalone XS/S/M/L/XL/XXL
    size_match = re.search(
        r'(?:size\s+|in\s+(?:a\s+)?|in\s+size\s+)?(XS|S\b|M\b|L\b|XL|XXL|S\/M|one\s+size)',
        query,
        re.IGNORECASE,
    )
    size = size_match.group(1).upper() if size_match else None

    # Build description: remove price fragments and size fragments from query
    description = query
    if price_match:
        description = description[:price_match.start()] + description[price_match.end():]
    if size_match:
        # remove the full size phrase (e.g. "size M" or "in a L")
        description = re.sub(
            r'(?:size\s+|in\s+(?:a\s+)?|in\s+size\s+)?(XS|S\b|M\b|L\b|XL|XXL|S\/M|one\s+size)',
            '',
            description,
            flags=re.IGNORECASE,
        )

    # Clean up leftover filler words and punctuation
    description = re.sub(
        r'\b(looking for|i want|find me|show me|under|less than|for|a|an|the|,)\b',
        ' ',
        description,
        flags=re.IGNORECASE,
    )
    description = re.sub(r'\s+', ' ', description).strip(' ,.-')

    return {
        "description": description,
        "size": size,
        "max_price": max_price,
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Args:
        query:    Natural language user request
                  (e.g., "vintage graphic tee under $30, size M")
        wardrobe: User's wardrobe dict — use get_example_wardrobe() or
                  get_empty_wardrobe() from utils/data_loader.py

    Returns:
        The session dict after the interaction completes. Check session["error"]
        first — if it is not None, the interaction ended early and the other
        output fields (outfit_suggestion, fit_card) will be None.
    """

    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse the query into structured parameters
    parsed = _parse_query(query)
    session["parsed"] = parsed

    description = parsed["description"]
    size = parsed["size"]
    max_price = parsed["max_price"]

    # Guard: if description is empty after parsing, we can't search meaningfully
    if not description:
        session["error"] = (
            "I couldn't understand what you're looking for. "
            "Try something like: 'vintage graphic tee under $30, size M'."
        )
        return session

    # Step 3: Call search_listings with parsed parameters
    results = search_listings(description, size=size, max_price=max_price)
    session["search_results"] = results

    # Early exit if no listings matched
    if not results:
        price_hint = f" under ${int(max_price)}" if max_price else ""
        size_hint = f" in size {size}" if size else ""
        session["error"] = (
            f"No listings found for '{description}'{size_hint}{price_hint}. "
            "Try broadening your search — use a higher price limit, skip the size filter, "
            "or use different keywords."
        )
        return session

    # Step 4: Select the top result (highest relevance score from search_listings)
    session["selected_item"] = results[0]

    # Step 5: Call suggest_outfit with the selected item and user's wardrobe
    # If wardrobe is empty, suggest_outfit handles it gracefully with general advice
    outfit_suggestion = suggest_outfit(session["selected_item"], session["wardrobe"])
    session["outfit_suggestion"] = outfit_suggestion

    # Step 6: Call create_fit_card with the outfit suggestion and selected item
    # If outfit_suggestion is somehow empty, create_fit_card handles it gracefully
    fit_card = create_fit_card(session["outfit_suggestion"], session["selected_item"])
    session["fit_card"] = fit_card

    # Step 7: Return the completed session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

# if __name__ == "__main__":
#     from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

#     print("=== Happy path: graphic tee ===\n")
#     session = run_agent(
#         query="looking for a vintage graphic tee under $30",
#         wardrobe=get_example_wardrobe(),
#     )
#     if session["error"]:
#         print(f"Error: {session['error']}")
#     else:
#         print(f"Found: {session['selected_item']['title']}")
#         print(f"\nOutfit: {session['outfit_suggestion']}")
#         print(f"\nFit card: {session['fit_card']}")

#     print("\n\n=== No-results path ===\n")
#     session2 = run_agent(
#         query="designer ballgown size XXS under $5",
#         wardrobe=get_example_wardrobe(),
#     )
#     print(f"Error message: {session2['error']}")
if __name__ == "__main__":
    from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

    # ── Test 1: Happy path with state verification ────────────────────────────
    print("=== Happy path: vintage graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=get_example_wardrobe(),
    )

    if session["error"]:
        print(f"ERROR (unexpected): {session['error']}")
    else:
        print("✅ selected_item:")
        print(session["selected_item"])

        # Verify state passed correctly into suggest_outfit
        # suggest_outfit receives session["selected_item"] directly —
        # confirm it's a real dict with the expected fields, not None or a copy
        assert session["selected_item"] is not None, "selected_item is None"
        assert isinstance(session["selected_item"], dict), "selected_item is not a dict"
        assert "title" in session["selected_item"], "selected_item missing 'title'"
        assert "price" in session["selected_item"], "selected_item missing 'price'"
        print("\n✅ selected_item is a valid listing dict — state passed correctly into suggest_outfit")

        print("\n✅ outfit_suggestion (passed into create_fit_card):")
        print(session["outfit_suggestion"])
        assert session["outfit_suggestion"], "outfit_suggestion is empty or None"
        assert isinstance(session["outfit_suggestion"], str), "outfit_suggestion is not a string"
        print("\n✅ outfit_suggestion is a non-empty string — state passed correctly into create_fit_card")

        print("\n✅ fit_card (final output):")
        print(session["fit_card"])
        assert session["fit_card"], "fit_card is empty or None"

    # ── Test 2: No-results branch ─────────────────────────────────────────────
    print("\n\n=== No-results path: designer ballgown XXS under $5 ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=get_example_wardrobe(),
    )

    assert session2["error"] is not None, "Expected an error message but got None"
    assert session2["fit_card"] is None, f"fit_card should be None but got: {session2['fit_card']}"
    assert session2["outfit_suggestion"] is None, f"outfit_suggestion should be None but got: {session2['outfit_suggestion']}"
    assert session2["selected_item"] is None, f"selected_item should be None but got: {session2['selected_item']}"
    print(f"✅ Error message: {session2['error']}")
    print("✅ fit_card is None — suggest_outfit and create_fit_card were not called")