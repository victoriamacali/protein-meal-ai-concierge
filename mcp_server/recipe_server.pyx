from mcp.server.fastmcp import FastMCP

mcp = FastMCP("recipe-server")

INGREDIENT_DATA = {
    "ground beef":   {"protein_g": 26, "est_price": 5.00},
    "pasta":         {"protein_g": 7,  "est_price": 1.50},
    "eggs":          {"protein_g": 6,  "est_price": 0.30},
    "greek yogurt":  {"protein_g": 10, "est_price": 1.00},
    "cheddar":       {"protein_g": 7,  "est_price": 1.20},
    "chicken breast":{"protein_g": 31, "est_price": 3.50},
    "tofu":          {"protein_g": 10, "est_price": 1.80},
    "black beans":   {"protein_g": 8,  "est_price": 0.90},
    "parmesan":      {"protein_g": 8,  "est_price": 0.80},
}

@mcp.tool()
def lookup_recipes(have_ingredients: list[str]) -> dict:
    """Suggests a protein-forward recipe using ingredients the user already
    has on hand, plus data on protein content and estimated price for any
    ingredients that might be added.

    Args:
        have_ingredients: ingredients the user says they currently have
    Returns:
        dict with a recipe name, the matched base ingredients (with protein/
        price data), and suggested protein-boosting additions.
    """
    have = [i.lower().strip() for i in have_ingredients]
    base = [
        {"name": name, **data}
        for name, data in INGREDIENT_DATA.items()
        if name in have
    ]
    additions = sorted(
        (
            {"name": name, **data}
            for name, data in INGREDIENT_DATA.items()
            if name not in have
        ),
        key=lambda x: -x["protein_g"],
    )[:3]

    recipe_name = "Beef & Pasta Skillet" if "ground beef" in have and "pasta" in have else "Protein-Boosted Skillet"

    return {
        "recipe_name": recipe_name,
        "base_ingredients": base,
        "suggested_additions": additions,
    }

if __name__ == "__main__":
    mcp.run()
