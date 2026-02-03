from mcp.server.fastmcp import FastMCP
from .config import (
    SERVER_HOST,
    SERVER_PORT
)
import json

mcp = FastMCP("CalorieTracker", host=SERVER_HOST, port=SERVER_PORT)

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

    file_path = 'mock_data.json'
    with open(file_path, 'r') as f:
        data = json.load(f)

    print(data)
    return "data logged"

@mcp.tool()
def get_today_summary() -> str:
    """
    Get a summary of today's meals and calorie intake.

    Returns:
        Summary of all meals logged today with totals
    """
    response = 'all good'
    print(response)
    return response
    

def main():
    mcp.run(transport="streamable-http")

if __name__ == '__main__':
    main()