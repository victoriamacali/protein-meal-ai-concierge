import os
import sys
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import ToolContext
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.genai import types

SERVER_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "mcp_server", "recipe_server.py"
)


def check_protein_density(
    ingredients: list[dict], tool_context: ToolContext, min_protein_g: int = 25
) -> dict:
    """Estimates total protein for a meal and flags if it's below target.

    Args:
        ingredients: list of {"name": str, "protein_g": float}
        min_protein_g: minimum grams of protein required for the meal
    Returns:
        dict with status ('meets_target' or 'below_target'), total protein, target
    """
    total = sum(i.get("protein_g", 0) for i in ingredients)
    status = "meets_target" if total >= min_protein_g else "below_target"
    result = {"status": status, "total_protein_g": total, "target": min_protein_g}
    tool_context.state["protein_check"] = result  # <-- record for the gate
    return result


def check_budget(
    grocery_list: list[dict], tool_context: ToolContext, max_budget: float
) -> dict:
    """Validates whether a grocery list of missing ingredients fits a budget.

    Args:
        grocery_list: list of {"name": str, "est_price": float}
        max_budget: user's maximum spend for missing items
    Returns:
        dict with status ('within_budget' or 'over_budget'), total cost, overage
    """
    total = sum(i.get("est_price", 0) for i in grocery_list)
    status = "within_budget" if total <= max_budget else "over_budget"
    result = {
        "status": status,
        "total_cost": round(total, 2),
        "over_by": round(max(0, total - max_budget), 2),
    }
    tool_context.state["budget_check"] = result  # <-- record for the gate
    return result


def enforce_guardrails(callback_context: CallbackContext):
    """Hard gate: runs after every agent turn. If the agent answered without
    a passing protein check, blocks the response instead of trusting the LLM
    to have followed the instruction on its own.
    """
    state = callback_context.state.to_dict()
    protein_check = state.get("protein_check")
    budget_check = state.get("budget_check")

    # If a protein check never ran, or ran and failed, block the response.
    if not protein_check or protein_check.get("status") != "meets_target":
        return types.Content(
            role="model",
            parts=[types.Part(text=(
                "I can't finalize this meal plan — I either haven't verified "
                "its protein content yet, or it didn't meet the target. "
                "Let me look for a higher-protein option."
            ))],
        )

    # If the user gave a budget and it was checked and failed, also block.
    if budget_check and budget_check.get("status") == "over_budget":
        return types.Content(
            role="model",
            parts=[types.Part(text=(
                f"That grocery list is ${budget_check['over_by']} over your "
                "budget. Let me find a cheaper substitution before finalizing."
            ))],
        )

    return None  # both checks passed (or budget wasn't required) — allow response through


recipe_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,
            args=[SERVER_SCRIPT],
        ),
        timeout=30,
    ),
)

root_agent = Agent(
    name="protein_meal_concierge",
    model="gemini-flash-latest",
    instruction=(
        "You are a protein-focused meal concierge. The user tells you what "
        "ingredients they already have and, optionally, a budget for anything "
        "extra they need to buy. Follow this process every time:\n"
        "1. Call lookup_recipes with the user's on-hand ingredients.\n"
        "2. Call check_protein_density on the combined base_ingredients + any "
        "suggested_additions you plan to include.\n"
        "3. Build a grocery list of ONLY the additions the user doesn't already "
        "have, using their name and est_price.\n"
        "4. If the user gave a budget, call check_budget on that grocery list.\n"
        "5. Present clearly: the recipe name, total protein achieved, and the "
        "final grocery list with total cost.\n"
        "Never fabricate protein or price values yourself — always get them "
        "from the tools. Your response will be rejected if you skip these checks."
    ),
    tools=[recipe_toolset, check_protein_density, check_budget],
    after_agent_callback=enforce_guardrails,
)
