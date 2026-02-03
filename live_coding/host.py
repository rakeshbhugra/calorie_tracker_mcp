import litellm
from mcp.client.streamable_http import streamable_http_client
import os
import httpx

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")

messages = []

system_prompt = """You are a helpful calorie tracking assistant.
You help users log their meals and track their daily calorie intake.
When a user tells you about food they ate, use the log_meal tool to record it.
When they ask about their progress, use get_today_summary.
Be encouraging and helpful about their nutrition goals."""

async def main():
    print('host is starting')

    headers = {}
    async with httpx.AsyncClient(headers=headers) as http_client:
        async with streamable_http_client(MCP_SERVER_URL, http_client=http_client) as (
            read_stream,
            write_stream,
            _,
        ):
        
            while True:
                user_input = input('You: ').strip()

                