"""Shared ADK tool-call and result events."""

from google.adk.events import Event
from google.adk.tools import FunctionTool
from google.genai import types


def reply(message: str) -> types.Content:
    return types.ModelContent(parts=[types.Part(text=message)])


def tool_call(tool: FunctionTool, call_id: str, args: dict[str, str]) -> Event:
    return Event(
        content=types.ModelContent(
            parts=[
                types.Part(
                    function_call=types.FunctionCall(
                        id=call_id, name=tool.name, args=args
                    )
                )
            ]
        )
    )


def tool_result(tool: FunctionTool, call_id: str, status: str, code: str) -> Event:
    return Event(
        content=types.UserContent(
            parts=[
                types.Part(
                    function_response=types.FunctionResponse(
                        id=call_id,
                        name=tool.name,
                        response={"status": status, "code": code},
                    )
                )
            ]
        )
    )
