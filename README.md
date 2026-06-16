# FitFindr

A multi-tool AI agent that helps users find secondhand clothing and figure out how to wear it. Built for CodePath AI Engineering, Project 2.

---

## Tool Inventory

**search_listings(description: str, size: str | None, max_price: float | None) -> list[dict]**

Searches the mock listings dataset for items matching the user's keywords, optional size, and optional price ceiling. Filters by price and size first, then scores each remaining listing by keyword overlap with the description. Returns a list of matching listing dicts sorted by relevance score, highest first. Returns an empty list if nothing matches — does not raise an exception.

**suggest_outfit(new_item: dict, wardrobe: dict) -> str**

Takes the selected listing and the user's wardrobe and asks the LLM for 1-2 outfit combinations. If the wardrobe has items, it names specific pieces from the wardrobe. If the wardrobe is empty, it falls back to general styling advice for the item's category and vibe. Always returns a non-empty string.

**create_fit_card(outfit: str, new_item: dict) -> str**

Generates a short, casual caption in the style of an OOTD Instagram post. Mentions the item name, price, and platform once each. Uses a higher LLM temperature so outputs vary across runs. If the outfit string is empty, returns a descriptive error message instead of raising an exception.

---

## How the Planning Loop Works

The loop is a guarded sequential pipeline inside `run_agent()`. It does not call all three tools unconditionally — the search result determines whether the loop continues.

Step 1: Parse the query with regex to extract description keywords, size, and max_price.

Step 2: Call `search_listings` with the parsed parameters. If results come back empty, set `session["error"]` with a message telling the user what to loosen (size filter, budget, or keywords) and return early. `suggest_outfit` is never called with empty input.

Step 3: Set `session["selected_item"]` to the top result and call `suggest_outfit` with it and the wardrobe. The wardrobe empty-check is handled inside the tool, so the loop does not need to branch on it.

Step 4: Call `create_fit_card` with the outfit suggestion and selected item. Store the result in `session["fit_card"]` and return the session.

---

## State Management

A single `session` dict is initialized at the start of each run and passed through every step. Each tool's output is written back into the session before the next tool runs, so nothing is re-entered or re-queried between steps.

Fields stored in session:

- `query`: the original user input
- `parsed`: the extracted description, size, and max_price
- `search_results`: the full list returned by search_listings
- `selected_item`: the exact dict at index 0 of search_results, passed by reference into suggest_outfit
- `wardrobe`: the wardrobe dict passed in at the start
- `outfit_suggestion`: the string returned by suggest_outfit, passed verbatim into create_fit_card
- `fit_card`: the string returned by create_fit_card
- `error`: None on success, or a message string if the loop terminated early

---

## Interaction Walkthrough

**User query:** "looking for a vintage graphic tee under $30"

**Step 1: search_listings**
- Input: description="vintage graphic tee", size=None, max_price=30.0
- Why: the query contains price information and item keywords, so the loop parses and searches first
- Output: list of matching listings sorted by relevance; top result is "Y2K Baby Tee — Butterfly Print" at $18.0 on Depop

**Step 2: suggest_outfit**
- Input: new_item=Y2K Baby Tee dict, wardrobe=example wardrobe (10 items)
- Why: a match was found, so the loop proceeds to styling; selected_item flows directly from search results
- Output: two outfit combinations naming specific wardrobe pieces — baggy straight-leg jeans with chunky white sneakers for a retro look, and wide-leg khaki trousers with black combat boots for a chic contrast

**Step 3: create_fit_card**
- Input: outfit=the suggestion string above, new_item=Y2K Baby Tee dict
- Why: outfit suggestion is populated, so the loop generates a shareable caption
- Output: "I'm obsessed with my new Y2K Baby Tee that I scored on depop for $18.0 - it's giving me all the nostalgic feels. I paired it with some baggy straight-leg jeans and black combat boots for a chill, laid-back vibe, and I'm totally feeling the early 2000s nostalgia. The butterfly print is everything and more, and I love how it adds a playful touch to my overall look."

**Final output to user:** three panels populate: the listing details, the outfit suggestion naming their wardrobe pieces, and the fit card caption.

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listings match the query | Returns `[]`. Loop sets `session["error"]` with a message naming what to loosen (size filter, budget, keywords) and returns early. `suggest_outfit` is never called. |
| `suggest_outfit` | Wardrobe is empty | Detects `wardrobe["items"] == []` and switches to a general styling advice prompt. Returns a non-empty string instead of crashing. |
| `create_fit_card` | Outfit string is empty or whitespace | Returns `"Couldn't write a fit card — no outfit was provided."` without raising. |

---

## Spec Reflection

**One way planning.md helped during implementation:**

Writing out the size normalization logic in the spec before touching any code forced me to think through the messiness of the size field upfront. The listings have sizes like "S/M", "XL (oversized)", and "One Size" mixed together, and having a concrete matching strategy written down meant I wasn't figuring it out mid-implementation. The spec decision to strip parentheticals and split on slashes translated almost directly into the `normalize_size_tokens` function in `tools.py`.

**One divergence from your spec, and why:**

The spec described the planning loop as having a distinct "parse query" step that could optionally use an LLM. In practice, the regex parser worked well enough for the test queries that I kept it as pure regex and did not add an LLM fallback. The tradeoff is that unusual phrasings like "thirty dollars max" would not parse correctly, but for the scope of this project the regex approach was faster and more predictable.

---

## AI Usage

**Instance 1: size normalization edge cases**

While writing `search_listings` I ran into the messy size field  values like "S/M", "XL (oversized)", and "One Size" were not matching correctly with a basic string comparison. I asked Claude whether stripping parenthetical qualifiers before splitting would cover most cases. It confirmed the approach and I added the regex sub to handle that. I ran the tool manually against several listings with non-standard sizes to verify it was working before moving on.

**Instance 2: planning loop structure review**

After writing `run_agent()` I asked Claude to look at my session dict flow and confirm that `selected_item` was being passed by reference into `suggest_outfit` rather than re-queried. It pointed out that the way I had it written was fine but suggested printing the session at the end of a test run to visually verify the state — which I did. I did not change the core logic, just used it as a sanity check.
