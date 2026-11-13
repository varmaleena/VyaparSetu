"""ADK entry point for the VyaparSetu workflow."""

from google.adk.agents import SequentialAgent

root_agent = SequentialAgent(
    name="vyaparsetu",
    description="VyaparSetu supplier invoice workflow.",
    sub_agents=[],
)
