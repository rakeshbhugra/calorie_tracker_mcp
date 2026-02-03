"""
Calorie Tracker MCP Server

MCP server with OAuth authentication (Keycloak) that provides:
- log_meal: Log a meal with calories
- get_today_summary: Get today's meals and total calories

Run with:
    uv run python -m calorie_tracker.server

Environment variables:
    OAUTH_ISSUER_URL: Keycloak realm URL (e.g., http://localhost:8180/realms/mcp)
    OAUTH_AUDIENCE: Client ID (default: calorie-tracker)
    OAUTH_CLIENT_SECRET: Client secret for token exchange

Without OAUTH_ISSUER_URL, server runs without authentication.
"""

from mcp.server.fastmcp import FastMCP
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from .config import (
    SERVER_HOST,
    SERVER_PORT,
    RESOURCE_SERVER_URL,
    OAUTH_ISSUER_URL,
    OAUTH_AUDIENCE,
    DAILY_CALORIE_GOAL,
)
from .storage import load_meals, add_meal


# =============================================================================
# MCP Server Setup
# =============================================================================

if OAUTH_ISSUER_URL:
    from .auth import create_oauth_verifier

    mcp = FastMCP(
        "CalorieTracker",
        host=SERVER_HOST,
        port=SERVER_PORT,
        token_verifier=create_oauth_verifier(),
        auth=AuthSettings(
            issuer_url=AnyHttpUrl(OAUTH_ISSUER_URL),
            resource_server_url=AnyHttpUrl(RESOURCE_SERVER_URL),
            required_scopes=[],
        ),
    )

    # Register OAuth proxy routes for Claude.ai integration
    from .oauth_proxy import register_oauth_routes
    register_oauth_routes(mcp)
else:
    mcp = FastMCP("CalorieTracker", host=SERVER_HOST, port=SERVER_PORT)


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool()
def log_meal(food: str, calories: int) -> str:
    """
    Log a meal with its calorie count.

    Args:
        food: Description of the food (e.g., "2 eggs and toast")
        calories: Estimated calories

    Returns:
        Confirmation message with running total
    """
    add_meal(food, calories)
    meals = load_meals()

    total = sum(m["calories"] for m in meals)
    remaining = DAILY_CALORIE_GOAL - total

    return f"Logged: {food} ({calories} cal). Today's total: {total}/{DAILY_CALORIE_GOAL} cal. Remaining: {remaining} cal."


@mcp.tool()
def get_today_summary() -> str:
    """
    Get a summary of today's meals and calorie intake.

    Returns:
        Summary of all meals logged today with totals
    """
    meals = load_meals()

    if not meals:
        return f"No meals logged today. Daily goal: {DAILY_CALORIE_GOAL} cal."

    total = sum(m["calories"] for m in meals)
    remaining = DAILY_CALORIE_GOAL - total

    summary = "Today's Meals:\n"
    for i, meal in enumerate(meals, 1):
        summary += f"  {i}. {meal['food']} - {meal['calories']} cal\n"

    summary += f"\nTotal: {total}/{DAILY_CALORIE_GOAL} cal"
    summary += f"\nRemaining: {remaining} cal"

    if remaining < 0:
        summary += " (over budget!)"

    return summary


# =============================================================================
# Main
# =============================================================================

def main():
    """Run the MCP server."""
    print(f"Starting CalorieTracker MCP server on {SERVER_HOST}:{SERVER_PORT}")
    if OAUTH_ISSUER_URL:
        print("Authentication: ENABLED (OAuth/Keycloak)")
        print(f"  Issuer: {OAUTH_ISSUER_URL}")
        print(f"  Audience: {OAUTH_AUDIENCE}")
    else:
        print("Authentication: DISABLED (development mode)")
        print("  Set OAUTH_ISSUER_URL to enable OAuth")
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
