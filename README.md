# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.


# FitFindr

FitFindr is an AI-powered thrift shopping assistant. You describe what you're looking for in plain English, and the agent finds matching secondhand listings, suggests how to style the item with your existing wardrobe, and writes a shareable outfit caption — all from a single query.

---

## Tool Inventory

### `search_listings(description: str, size: str | None, max_price: float | None) → list[dict]`

Searches the mock listings dataset for secondhand items that match the user's query. It loads all 40 listings via `load_listings()`, filters by `size` (case-insensitive substring match, so "M" matches "S/M") and `max_price` (inclusive ceiling), then scores each remaining listing by counting how many of the description's keywords appear across `title`, `description`, and `style_tags`. Listings with a score of zero are dropped; the rest are returned sorted by score, highest first.

Each dict in the returned list contains: `id`, `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list), `brand`, and `platform`. Returns an empty list — never raises — when nothing matches.

---

### `suggest_outfit(new_item: dict, wardrobe: dict) → str`

Takes the selected listing and the user's wardrobe and asks the Groq LLM to suggest 1–2 complete outfit combinations. If `wardrobe["items"]` is empty, it prompts the LLM for general styling advice instead — what types of pieces pair well with the item and what aesthetic it suits. If the wardrobe has items, it formats them into the prompt by name, category, colors, and style tags, and asks the LLM to suggest specific named combinations with a rationale.

Returns a non-empty string in both cases. Never returns an empty string or raises an exception.

---

### `create_fit_card(outfit: str, new_item: dict) → str`

Takes the outfit suggestion string and the selected listing and asks the LLM to write a 2–4 sentence Instagram/TikTok-style caption. The prompt instructs the model to mention the item name, price, and platform once each, capture the outfit vibe in specific terms, and sound casual rather than like a product description. Uses `temperature=0.9` so captions vary across runs.

Returns a non-empty string. If `outfit` is empty or whitespace-only, skips the LLM call and returns a plain error message string describing what went wrong.

---

## Planning Loop

The agent parses the user's query using regex to extract three structured fields — `description`, `size`, and `max_price` — then calls the three tools in a fixed sequence, passing the output of each step into the next via the session dict.

The conditional logic works as follows:

1. If the query is blank, return an error immediately without calling any tool.
2. Call `search_listings` with the parsed fields. If the result is an empty list, set `session["error"]` to a message explaining what to try differently and return the session early. Do not call `suggest_outfit` or `create_fit_card`.
3. If results exist, set `session["selected_item"] = results[0]` and call `suggest_outfit`. Even if the wardrobe is empty, `suggest_outfit` always returns a usable string, so the loop never exits early here.
4. Call `create_fit_card` with the outfit string. Even if the string is unexpectedly empty, `create_fit_card` returns a fallback message rather than raising, so the loop always completes.
5. Return the session.

The loop has exactly one early-exit branch: the empty search results case. Everything else runs to completion.

---

## State Management

All state for a single interaction lives in a session dict initialized by `_new_session()` at the start of `run_agent()`. The dict holds the original query, parsed parameters, and one field per tool output:

- `session["parsed"]` — set after query parsing, read by `search_listings`
- `session["search_results"]` — set after `search_listings`, used to populate `selected_item`
- `session["selected_item"]` — set to `results[0]`, passed directly into `suggest_outfit`
- `session["outfit_suggestion"]` — set after `suggest_outfit`, passed directly into `create_fit_card`
- `session["fit_card"]` — set after `create_fit_card`, returned to the UI
- `session["error"]` — set on early exit, left as `None` on success

The wardrobe is loaded once before `run_agent()` is called and passed in as an argument — it is never reloaded mid-run. Each tool reads exactly what the previous step wrote; no tool re-parses the original query or re-loads data independently.

---

## Error Handling

**`search_listings`** — if no listings match the query, the agent sets `session["error"]` and returns the session without calling the remaining tools. For example, querying `"designer ballgown size XXS under $5"` returns an empty list because no listing is priced below $5 at that size. The error message reads: *"No listings found for 'designer ballgown' in size XXS under $5. Try broadening your search — use a higher price limit, skip the size filter, or use different keywords."* `session["fit_card"]` and `session["outfit_suggestion"]` remain `None`.

**`suggest_outfit`** — if the wardrobe passed in has an empty `items` list, the tool does not crash or return an empty string. In testing with `get_empty_wardrobe()`, it returned a full paragraph of general styling advice — for example, suggesting pairing a vintage graphic tee with high-waisted denim and chunky sneakers based on the item's style tags alone — and the loop continued normally to `create_fit_card`.

**`create_fit_card`** — if `outfit` is an empty or whitespace-only string, the function returns the message `"Could not generate a caption: no outfit suggestion was provided."` without calling the LLM. This was tested directly by passing `""` and `"   "` as the outfit argument; both returned the error string and neither raised an exception.

---

## Spec Reflection

The implementation matches the planning spec in structure but diverged in one detail: the original spec described `suggest_outfit` returning a dict with `outfit` and `reasoning` keys, but the actual `tools.py` signature returns a plain string. The planning loop was adjusted accordingly — `session["outfit_suggestion"]` stores a string, not a dict, and `create_fit_card` receives that string directly.

The query parser works well for common phrasings like `"vintage graphic tee under $30, size M"` but is brittle around ambiguous size tokens — a query like `"find me something small"` would not extract a size, while `"looking for a medium weight jacket"` might incorrectly extract `"M"` as a size. A more robust implementation would use the LLM to parse the query rather than regex, which would handle natural language size references and edge cases more reliably. That would be the first thing to change in a production version.

## AI Usage

**Instance 1 — Implementing `search_listings`**
I gave Claude the Tool 1 block from `planning.md` (input parameters, return value description, failure mode) along with the `load_listings()` signature from `data_loader.py` and asked it to implement the filtering and scoring logic. The generated code was correct for price and size filtering but initially scored listings only against `title` — it missed `description` and `style_tags`. I overrode that by specifying the exact fields to search across, which matched what the planning spec said. I then tested it with three queries (a matching query, a price-too-low query, and a nonsense description) before trusting it.

**Instance 2 — Implementing `run_agent`**
I gave Claude the Planning Loop section, State Management section, and Architecture diagram from `planning.md` together and asked it to implement the full loop as a single function that reads and writes the session dict as specced. The first output used hardcoded fallback strings between tool calls instead of passing session values — for example, it passed `outfit_suggestion` as a new variable rather than reading from `session["outfit_suggestion"]`. I caught this by printing `session["selected_item"]` before and after the `suggest_outfit` call and confirming the same dict object was flowing through. I revised the implementation to pass session fields directly so state was never duplicated or reconstructed mid-run.