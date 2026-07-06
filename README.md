# Protein Meal Concierge

An AI agent that turns "here's what's in my kitchen" into a protein-optimized
meal plan and a budget-capped grocery list — built for the *AI Agents:
Intensive Vibe Coding* capstone (Concierge Agents track).

## Problem

Most meal-planning tools optimize for variety, convenience, or general
"healthy eating" — not for a specific, measurable macro target. People
trying to hit a protein goal (strength training, recovery, general fitness)
still have to manually check nutrition labels, do the math themselves, and
separately worry about staying within budget when buying extra ingredients.

## Solution

Protein Meal Concierge takes what you already have in your kitchen, plus an
optional budget, and:

1. Finds a protein-forward recipe built around your on-hand ingredients
2. Verifies the meal actually meets a protein target — and revises if it
   doesn't, rather than just asserting it does
3. Builds a grocery list of only the ingredients you're missing
4. Verifies that list fits your stated budget — and trims/substitutes if
   it doesn't

The key design goal: **the agent never just claims a number is correct — it
calls a tool to check.** Early in development, the agent (without proper
tool wiring) fabricated a plausible-sounding recipe with made-up protein and
price figures. The architecture below exists specifically to prevent that.

## Architecture
User prompt
│
▼
┌─────────────────────────┐
│  ADK Agent               │
│  (protein_meal_concierge)│
└─────────────────────────┘
│
├──► MCP Tool: lookup_recipes(have_ingredients)
│     → runs on a separate local MCP server (recipe_server.py)
│     → returns a candidate recipe + protein/price data per ingredient
│
├──► Guardrail Tool: check_protein_density(ingredients, min_protein_g)
│     → sums real protein data, flags if under target
│     → agent must revise the plan and re-check if it fails
│
└──► Guardrail Tool: check_budget(grocery_list, max_budget)
→ sums real price data, flags if over budget
→ agent must substitute/trim and re-check if it fails

**Why MCP for the recipe lookup specifically:** it keeps ingredient/nutrition
data as a separately runnable service rather than baked into the agent's own
code — the same pattern used for connecting an agent to any external data
source (a real nutrition API could swap in here with no agent-side changes).

**Why two guardrails instead of one combined check:** protein and budget are
independent constraints that can each fail on their own; keeping them as
separate tools makes the failure mode explicit in the trace (you can see
*which* constraint the agent is reacting to) rather than a single opaque
"is this plan okay?" check.

## Tech Stack

- **Google ADK** (`google-adk`) — agent framework, tool orchestration
- **Model Context Protocol** (`mcp`) — local recipe/nutrition lookup server
- **Gemini** (`gemini-2.5-flash` / `gemini-flash-latest`) — underlying LLM
- **Antigravity IDE/CLI** — used for local development and testing (see demo video)

## Setup

```bash
git clone https://github.com/victoriamacali/protein-meal-ai-concierge.git
cd protein-meal-ai-concierge

python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Create a `.env` file in the project root with your Gemini API key
(get one at https://aistudio.google.com/app/apikey):
GOOGLE_API_KEY=your_key_here

Run the agent:
```bash
adk run agent_app
```
or, for a visual trace of tool calls:
```bash
adk web agent_app
```

## Example interaction
[user]: I have pasta and ground beef, I want a meal with 25-35 grams of
protein, keep extra ingredients under $15
[protein_meal_concierge]: Recipe: Beef & Pasta Skillet
Total protein: 41g (target: 25-35g ✓)
Grocery list (missing ingredients only):

Parmesan: $0.80
Total cost: $0.80 (within $15.00 budget)


## Security / Guardrails

- The agent is instructed to **never fabricate** nutrition or price data —
  all numbers must come from tool calls, not the LLM's own estimate
- `check_protein_density` and `check_budget` act as hard verification steps
  the agent must pass before presenting a final plan
- API keys are kept in `.env`, excluded from version control via `.gitignore`

## Known limitations / future work

- Ingredient/nutrition data is a small static lookup table for demo purposes
  — a production version would call a real nutrition API via the same MCP
  interface with no agent-side changes needed
- No persistent memory of user preferences across sessions (yet) — each
  session starts fresh
- No live deployment; runs locally via Antigravity/ADK CLI

## Track

Concierge Agents — automating a daily personal task (deciding what to eat
and what to buy) using tool-verified, constraint-driven agent reasoning.
