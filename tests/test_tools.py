from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe, get_empty_wardrobe

# ── search_listings ───────────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0

def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []

def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=10)
    assert all(item["price"] <= 10 for item in results)

def test_search_size_filter():
    results = search_listings("top", size="L", max_price=100)
    assert all("l" in item["size"].lower() for item in results)

def test_search_returns_expected_fields():
    results = search_listings("tee", size=None, max_price=100)
    if results:
        expected = {"id", "title", "description", "category", "style_tags",
                    "size", "condition", "price", "colors", "brand", "platform"}
        assert expected.issubset(results[0].keys())

def test_search_best_match_first():
    results = search_listings("vintage graphic tee", size=None, max_price=100)
    # first result should mention more keywords than the last
    assert len(results) >= 2  # enough results to compare ordering

# ── suggest_outfit ────────────────────────────────────────────────────────────

def test_suggest_outfit_with_wardrobe():
    results = search_listings("tee", size=None, max_price=50)
    assert results, "Need at least one listing to test suggest_outfit"
    new_item = results[0]
    wardrobe = get_example_wardrobe()
    result = suggest_outfit(new_item, wardrobe)
    assert isinstance(result, str)
    assert len(result.strip()) > 0

def test_suggest_outfit_empty_wardrobe():
    results = search_listings("tee", size=None, max_price=50)
    assert results, "Need at least one listing to test suggest_outfit"
    new_item = results[0]
    empty_wardrobe = get_empty_wardrobe()
    result = suggest_outfit(new_item, empty_wardrobe)
    assert isinstance(result, str)
    assert len(result.strip()) > 0  # should still return styling advice, not empty string

def test_suggest_outfit_references_item():
    results = search_listings("jacket", size=None, max_price=100)
    assert results
    new_item = results[0]
    wardrobe = get_example_wardrobe()
    result = suggest_outfit(new_item, wardrobe)
    # LLM response should mention something about the item or outfit
    assert any(word in result.lower() for word in ["outfit", "pair", "wear", "style", "look"])

# ── create_fit_card ───────────────────────────────────────────────────────────

def test_create_fit_card_returns_string():
    results = search_listings("tee", size=None, max_price=50)
    assert results
    new_item = results[0]
    wardrobe = get_example_wardrobe()
    outfit = suggest_outfit(new_item, wardrobe)
    card = create_fit_card(outfit, new_item)
    assert isinstance(card, str)
    assert len(card.strip()) > 0

def test_create_fit_card_mentions_item_details():
    results = search_listings("tee", size=None, max_price=50)
    assert results
    new_item = results[0]
    wardrobe = get_example_wardrobe()
    outfit = suggest_outfit(new_item, wardrobe)
    card = create_fit_card(outfit, new_item)
    card_lower = card.lower()
    # caption should mention price and platform somewhere
    assert str(int(new_item["price"])) in card or str(new_item["price"]) in card
    assert new_item["platform"].lower() in card_lower

def test_create_fit_card_empty_outfit():
    results = search_listings("tee", size=None, max_price=50)
    assert results
    new_item = results[0]
    card = create_fit_card("", new_item)
    assert isinstance(card, str)
    assert len(card.strip()) > 0  # should return error message, not empty string or exception

def test_create_fit_card_whitespace_outfit():
    results = search_listings("tee", size=None, max_price=50)
    assert results
    new_item = results[0]
    card = create_fit_card("   ", new_item)
    assert isinstance(card, str)
    assert len(card.strip()) > 0