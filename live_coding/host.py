import litellm
from litellm import experimental_mcp_client
from mcp.client.streamable_http import streamable_http_client
from mcp import ClientSession
import os
import httpx
import asyncio

MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")

messages = []

system_prompt = """You are a helpful calorie tracking assistant.
You help users log their meals and track their daily calorie intake.
When a user tells you about food they ate, use the log_meal tool to record it.
When they ask about their progress, use get_today_summary.
Be encouraging and helpful about their nutrition goals."""

messages.append(
    {'role': 'system', 'content': system_prompt}
)


async def chat_loop(session, tools):
    while True:
        user_input = input('You: ').strip()

        messages.append(
            {'role': 'user', 'content': user_input}
        )
    

        response = await litellm.acompletion(
            model = 'openai/gpt-4.1-mini',
            messages=messages,
            tools = tools
        )

        assistant_message = response["choices"][0]["message"]

        print(assistant_message)

        if assistant_message.get('tool_calls'):
            messages.append(assistant_message)

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

                response = await litellm.acompletion(
                    model="openai/gpt-4o-mini",
                    messages=messages,
                    tools=tools
                )
                assistant_message = response["choices"][0]["message"]

        print(f"Assistant: {assistant_message['content']}\n")
        messages.append({"role": "assistant", "content": assistant_message["content"]})


async def main():
    print('host is starting')

    headers = {}
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
                
                print(tools)
        
                await chat_loop(session, tools)

                
if __name__ == '__main__':
    asyncio.run(main()) 