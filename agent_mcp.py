import asyncio
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import time
from google.genai.errors import ClientError
import json
from groq import Groq
from google.genai.errors import ClientError, ServerError

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
server_params = StdioServerParameters(command="python3", args=["mcp_server.py"])


def mcp_tool_to_gemini_declaration(mcp_tool):
    return types.FunctionDeclaration(
        name=mcp_tool.name,
        description=mcp_tool.description or "",
        parameters=mcp_tool.input_schema,
    )

def mcp_tool_to_openai_format(mcp_tool):
    return {
        "type": "function",
        "function": {
            "name": mcp_tool.name,
            "description": mcp_tool.description or "",
            "parameters": mcp_tool.input_schema,
        },
    }

async def investigate_with_groq(session, mcp_tools, anomaly_description: str) -> str:
    openai_tools = [mcp_tool_to_openai_format(t) for t in mcp_tools.tools]

    messages = [
        {
            "role": "system",
            "content": (
                "You are a site-reliability agent investigating a data pipeline anomaly. "
                "Use the available tools to gather evidence, determine a likely root cause "
                "and a severity of LOW, MEDIUM, or HIGH, then use the post_slack_alert tool "
                "to post your final diagnosis to Slack. Always call post_slack_alert as your "
                "last action before responding with a final summary."
            ),
        },
        {"role": "user", "content": anomaly_description},
    ]

    while True:
        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-120b",
            messages=messages,
            tools=openai_tools,
        )
        msg = response.choices[0].message

        if not msg.tool_calls:
            return msg.content

        messages.append(msg)
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"  [fallback agent is calling tool: {tc.function.name}({args})]")
            result = await session.call_tool(tc.function.name, arguments=args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": result.content[0].text,
            })

def send_with_retry(chat, content, max_retries=3):
    for attempt in range(max_retries):
        try:
            return chat.send_message(content)
        except (ClientError, ServerError) as e:
            code=getattr(e,"code", None)
            if code == 429 and attempt < max_retries - 1:
                wait = 20
                print(f"  [rate limited — waiting {wait}s before retry]")
                time.sleep(wait)
            else:
                raise

async def investigate_anomaly(anomaly_description: str) -> str:
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = await session.list_tools()

            try:
                gemini_tools = types.Tool(
                    function_declarations=[mcp_tool_to_gemini_declaration(t) for t in mcp_tools.tools]
                )

                chat = client.chats.create(
                    model="gemini-2.5-flash",
                    config=types.GenerateContentConfig(
                        tools=[gemini_tools],
                        system_instruction=(
                            "You are a site-reliability agent investigating a data pipeline anomaly. "
                            "Use the available tools to gather evidence, determine a likely root cause "
                            "and a severity of LOW, MEDIUM, or HIGH, then use the post_slack_alert tool "
                            "to post your final diagnosis to Slack. Always call post_slack_alert as your "
                            "last action before responding with a final summary."
                        ),
                    ),
                )

                response = send_with_retry(chat, anomaly_description)

                while response.function_calls:
                    function_responses = []
                    for fc in response.function_calls:
                        print(f"  [agent is calling tool: {fc.name}({dict(fc.args)})]")
                        result = await session.call_tool(fc.name, arguments=dict(fc.args))
                        function_responses.append(
                            types.Part.from_function_response(
                                name=fc.name,
                                response={"result": result.content[0].text},
                            )
                        )
                    response = send_with_retry(chat, function_responses)

                return response.text

            except (ClientError, ServerError) as e:
                print(f"  [Gemini unavailable ({e}), falling back to Groq]")
                return await investigate_with_groq(session, mcp_tools, anomaly_description)


if __name__ == "__main__":
    result = asyncio.run(
        investigate_anomaly(
            "Order volume dropped to near-zero around 12:46 for the checkout-service pipeline."
        )
    )
    print("\nFinal diagnosis:")
    print(result)