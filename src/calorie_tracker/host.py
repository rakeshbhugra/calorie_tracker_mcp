"""
Calorie Tracker MCP Host (Client)

Connects to the calorie tracker MCP server and provides a chat interface.

Run with:
    1. First start the server: uv run python -m calorie_tracker.server
    2. Then run this host: uv run python -m calorie_tracker.host

Environment variables:
    MCP_SERVER_URL: URL of the MCP server (default: http://localhost:8000/mcp)
    OAUTH_TOKEN_URL: Keycloak token endpoint
    OAUTH_CLIENT_ID: Keycloak client ID
    OAUTH_CLIENT_SECRET: Keycloak client secret
    OPENAI_API_KEY: OpenAI API key for LLM
"""

import asyncio
import os

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
import litellm
from litellm import experimental_mcp_client
from dotenv import load_dotenv

load_dotenv()

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
OAUTH_TOKEN_URL = os.getenv("OAUTH_TOKEN_URL", "http://localhost:8180/realms/mcp/protocol/openid-connect/token")
OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "calorie-tracker")
OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET")


def get_oauth_token() -> str | None:
    """Get OAuth token from Keycloak using client credentials."""
    if not OAUTH_CLIENT_SECRET:
        return None

    response = httpx.post(
        OAUTH_TOKEN_URL,
        data={
            "client_id": OAUTH_CLIENT_ID,
            "client_secret": OAUTH_CLIENT_SECRET,
            "grant_type": "client_credentials",
        },
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    print(f"Failed to get token: {response.text}")
    return None


async def chat_loop(session: ClientSession, tools: list):
    """Main chat loop with the LLM and MCP tools."""

    system_prompt = """You are a helpful calorie tracking assistant.
You help users log their meals and track their daily calorie intake.
When a user tells you about food they ate, use the log_meal tool to record it.
When they ask about their progress, use get_today_summary.
Be encouraging and helpful about their nutrition goals."""

    messages = [{"role": "system", "content": system_prompt}]

    print("\n" + "=" * 50)
    print("Calorie Tracker Chat")
    print("=" * 50)
    print("Tell me what you ate or ask about your progress.")
    print("Type 'quit' to exit.\n")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        if not user_input:
            continue

        messages.append({"role": "user", "content": user_input})

        # Get LLM response
        response = await litellm.acompletion(
            model="openai/gpt-4o-mini",
            messages=messages,
            tools=tools
        )

        assistant_message = response["choices"][0]["message"]

        # Check if LLM wants to call tools
        if assistant_message.get("tool_calls"):
            messages.append(assistant_message)

            # Execute each tool call
            for tool_call in assistant_message["tool_calls"]:
                print(f"  [Calling: {tool_call['function']['name']}]")

                result = await experimental_mcp_client.call_openai_tool(
                    session=session,
                    openai_tool=tool_call,
                )

                tool_result = result.content[0].text
                print(f"  [Result: {tool_result}]")

                messages.append({
                    "role": "tool",
                    "content": tool_result,
                    "tool_call_id": tool_call["id"],
                })

            # Get final response after tool execution
            response = await litellm.acompletion(
                model="openai/gpt-4o-mini",
                messages=messages,
                tools=tools
            )
            assistant_message = response["choices"][0]["message"]

        # Print assistant response
        print(f"Assistant: {assistant_message['content']}\n")
        messages.append({"role": "assistant", "content": assistant_message["content"]})


async def main():
    print(f"Connecting to MCP server at {MCP_SERVER_URL}...")

    # Get OAuth token from Keycloak
    headers = {}
    token = get_oauth_token()
    if token:
        headers["Authorization"] = f"Bearer {token}"
        print("Authentication: OAuth token obtained")
    else:
        print("Authentication: None (set OAUTH_CLIENT_SECRET to enable)")

    async with httpx.AsyncClient(headers=headers) as http_client:
        async with streamable_http_client(MCP_SERVER_URL, http_client=http_client) as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                # Load tools from MCP server
                tools = await experimental_mcp_client.load_mcp_tools(
                    session=session,
                    format="openai"
                )

                print(f"Loaded tools: {[t['function']['name'] for t in tools]}")

                # Start chat loop
                await chat_loop(session, tools)


if __name__ == "__main__":
    asyncio.run(main())
