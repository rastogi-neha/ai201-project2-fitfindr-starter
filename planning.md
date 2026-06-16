# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Searches the mock listings dataset for secondhand clothing items that match the user's description, size, and budget. It loads all listings via load_listings() and filters them by keyword match against title, description, and style_tags, then by size and price.
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): A natural language description of the item, matched against title, description, and style_tags
- `size` (str): The user's clothing size, matched against the listing's size field
- `max_price` (float): The maximum price the user will pay filters out any listing where price > max_price

**What it returns:**
<!-- Describe the return value — what fields does a result contain? -->
A list of listing dicts, each containing: id, title, description, category, style_tags, size, condition, price, colors, brand, platform. Returns an empty list if nothing matches.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
If the list is empty, the agent sets session["error"] = "No listings matched your search." and returns early with a user-facing message
---

### Tool 2: suggest_outfit

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Takes a single clothing item (the result selected from search_listings) and the user's wardrobe, and returns a suggested outfit by matching style tags, colors, and category against wardrobe items. It aims to pair the new item with 1–2 complementary pieces the user already owns.
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): A single listing dict from search_listings must include style_tags, colors, and category
- `wardrobe` (dict): A wardrobe dict with an items key containing a list of wardrobe item dicts, each with name, category, colors, and style_tags

**What it returns:**
<!-- Describe the return value -->
A dict with two keys: outfit (a list of 2–3 item dicts the new item plus matched wardrobe pieces) and reasoning (a short string explaining why the pieces work together)
**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If wardrobe["items"] is empty or no wardrobe item shares style tags or colors with new_item, the agent sets session["outfit"] = {"outfit": [new_item], "reasoning": "No wardrobe items to pair with — showing the item alone."} and proceeds to create_fit_card with just the single item.
---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
Takes the assembled outfit and formats it into a structured fit card, a dict the UI can render directly, combining item details, pairing notes, price, platform, and condition into one clean output object.
**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (...): The return value from suggest_outfit must have an outfit key (list of item dicts) and a reasoning key (str)

**What it returns:**
<!-- Describe the return value -->
A dict with: items (list of dicts, each with title, price, platform, condition, colors), reasoning (str copied from the outfit), and summary (a one-sentence string combining all three items and the styling rationale, ready to display to the user).
**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If outfit is missing the outfit key or the list is empty, the agent skips card creation and falls back to returning session["outfit"]["reasoning"] as plain text directly to the user, with a note that the card could not be generated.
---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->
1. Receive user message. Parse out description, size, and max_price.
   - If any required field is missing, ask the user a clarifying question and wait. Do not call any tool.

2. Call search_listings(description, size, max_price).
   - If results is empty:
       → set session["error"] = "No listings found"
       → return early with fallback message to user
       → stop here; do not call tools 2 or 3
   - If results is not empty:
       → set session["selected_item"] = results[0]
       → proceed to step 3

3. Call suggest_outfit(new_item=session["selected_item"], wardrobe=session["wardrobe"]).
   - If wardrobe is empty or no match found:
       → set session["outfit"] = {"outfit": [session["selected_item"]], "reasoning": "No wardrobe match found."}
   - Otherwise:
       → set session["outfit"] = return value from suggest_outfit
   - Always proceed to step 4

4. Call create_fit_card(outfit=session["outfit"]).
   - If outfit data is valid:
       → set session["fit_card"] = return value
       → return fit_card to user
   - If outfit data is invalid or missing:
       → return session["outfit"]["reasoning"] as plain text to user
---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->
The agent loads the user's wardrobe once at the start of every session using get_example_wardrobe() and stores it in session["wardrobe"] so it doesn't get reloaded on every tool call. As each tool completes, its output is written into the session — search_listings writes to session["selected_item"], suggest_outfit writes to session["outfit"], and create_fit_card writes to session["fit_card"] — so each tool always reads from what the previous one produced rather than taking raw user input.
---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query |Set session["error"], return early with "No results — try broadening your search", skip tools 2 and 3 |
| suggest_outfit | Wardrobe is empty |Set session["outfit"] to just the new item with a "no wardrobe match" reasoning string, still proceed to create_fit_card |
| create_fit_card | Outfit input is missing or incomplete |Skip card generation, return session["outfit"]["reasoning"] as plain text |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->
┌─────────────┐
│    User     │
│   Input     │
└──────┬──────┘
       │ description, size, max_price
       ▼
┌─────────────────────────────────────────────────────┐
│                   Planning Loop                     │
│                                                     │
│  1. Parse input → missing fields? → ask user        │
│  2. Call search_listings                            │
│     └─ empty? → set error → ──────────────────────┐│
│  3. Call suggest_outfit                             ││
│     └─ no match? → use item alone, continue        ││
│  4. Call create_fit_card                            ││
│     └─ invalid? → return plain text fallback ─────┐││
└─────────────────────────────────────────────────────┘│
       │                                               ││
       │ tool calls & returns                          ││
       ▼                                               ││
┌──────────────────────┐    ┌─────────────────────┐   ││
│   search_listings    │    │   Session State     │   ││
│  filters listings    │───▶│  selected_item      │   ││
│  by desc/size/price  │    │  wardrobe           │   ││
└──────────────────────┘    │  outfit             │   ││
┌──────────────────────┐    │  fit_card           │   ││
│   suggest_outfit     │◀──▶│  error              │   ││
│  matches new_item    │    └─────────────────────┘   ││
│  to wardrobe items   │                              ││
└──────────────────────┘                              ││
┌──────────────────────┐                              ││
│   create_fit_card    │                              ││
│  formats outfit into │                              ││
│  renderable card     │                              ││
└──────────┬───────────┘                              ││
           │                                          ││
           ▼                                          ││
┌─────────────────────┐   ◀───────────────────────────┘│
│   Output to User    │   ◀────────────────────────────┘
│  fit card or plain  │     (early exit / fallback paths)
│  text fallback      │
└─────────────────────┘
---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**

For search_listings, I'll give Claude the Tool 1 block from planning.md (input parameters, return value description, failure mode) plus the load_listings() signature from dataloader.py, and ask it to implement the function. Before trusting it I'll check that the generated code filters by all three parameters — description against title/description/style_tags, size as an exact match, and price as a ceiling — and that it returns an empty list (not None or an error) when nothing matches. Then I'll test it with three queries: one that should return results, one with a price too low to match anything, and one with a nonsense description.

For suggest_outfit, I'll give Claude the Tool 2 block from planning.md plus the get_example_wardrobe() signature and the wardrobe schema field definitions, and ask it to implement the matching logic. I'll verify the output always contains both an outfit key (a list) and a reasoning key (a string), and that when I pass in an empty wardrobe it still returns a valid dict with just the new item rather than crashing.

For create_fit_card, I'll give Claude the Tool 3 block from planning.md and a sample suggest_outfit return value, and ask it to format the fit card. I'll verify the output contains items, reasoning, and summary keys, that summary is a single human-readable string, and that passing in a malformed outfit dict produces the plain-text fallback rather than an exception.

**Milestone 4 — Planning loop and state management:**

I'll give Claude the Planning Loop section, the State Management section, and the Architecture diagram from planning.md together in one prompt, and ask it to implement the loop as a single function that calls the three tools in order and reads/writes the session dict as specified. Before using it I'll verify four things: that missing input triggers a clarifying question instead of a tool call, that an empty result from search_listings causes an early return without calling tools 2 or 3, that a failed suggest_outfit match still proceeds to create_fit_card, and that the final return value is either the fit card dict or the plain-text fallback — never None.
---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
<!-- What does the agent do first? Which tool is called? With what input? -->
The agent calls search_listings with description="vintage graphic tee", size inferred from context (or left open), and max_price=30.0. It scans the listings dataset for items whose style tags, category, and description match, returning a list of candidate tops under $30.
**Step 2:**
<!-- What happens next? What was returned from step 1? What tool is called now? -->
Using the best match from Step 1 (say, a vintage band tee at $22), the agent calls suggest_outfit with that item as new_item and the user's implied wardrobe — baggy jeans and chunky sneakers — as wardrobe. It returns a complete outfit pairing that fits the user's existing style.
**Step 3:**
<!-- Continue until the full interaction is complete -->
With the assembled outfit from Step 2, the agent calls create_fit_card passing the full outfit dict. It packages the item details, pairing suggestions, and styling notes into a structured fit card ready to display to the user.
**Final output to user:**
<!-- What does the user actually see at the end? -->
The user sees a fit card showing the specific listing (title, price, platform, condition), which pieces from their wardrobe to pair it with, and a short styling note explaining why the combination works — something like: "This vintage graphic tee at $22 on Depop pairs well with your baggy jeans and chunky sneakers for a relaxed streetwear look. Available in size M, condition: good."