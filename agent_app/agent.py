import os
import sys
from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

SERVER_SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "mcp_server", "recipe_server.py"
)


def check_protein_density(ingredients: list[dict], min_protein_g: int = 25) -> dict:
    """Estimates total protein for a meal and flags if it's below target.

    Args:
        ingredients: list of {"name": str, "protein_g": float}
        min_protein_g: minimum grams of protein required for the meal
    Returns:
        dict with status ('meets_target' or 'below_target'), total protein, target
    """
    total = sum(i.get("protein_g", 0) for i in ingredients)
    status = "meets_target" if total >= min_protein_g else "below_target"
    return {"status": status, "total_protein_g": total, "target": min_protein_g}


def check_budget(grocery_list: list[dict], max_budget: float) -> dict:
    """Validates whether a grocery list of missing ingredients fits a budget.

    Args:
        grocery_list: list of {"name": str, "est_price": float}
        max_budget: user's maximum spend for missing items
    Returns:
        dict with status ('within_budget' or 'over_budget'), total cost, overage
    """
    total = sum(i.get("est_price", 0) for i in grocery_list)
    status = "within_budget" if total <= max_budget else "over_budget"
    return {
        "status": status,
        "total_cost": round(total, 2),
        "over_by": round(max(0, total - max_budget), 2),
    }


recipe_toolset = MCPToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command=sys.executable,   # <-- was "python3", now the exact venv interpreter
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
        "suggested_additions you plan to include. If status is 'below_target', "
        "add more of the suggested high-protein additions and re-check.\n"
        "3. Build a grocery list of ONLY the additions the user doesn't already "
        "have, using their name and est_price.\n"
        "4. If the user gave a budget, call check_budget on that grocery list. "
        "If 'over_budget', drop the lowest-protein-per-dollar addition and "
        "re-check.\n"
        "5. Present clearly: the recipe name, total protein achieved, and the "
        "final grocery list with total cost.\n"
        "Never fabricate protein or price values yourself — always get them "
        "from the tools."
    ),
    tools=[recipe_toolset, check_protein_density, check_budget],
)
