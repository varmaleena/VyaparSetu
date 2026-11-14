"""ADK entry point for the VyaparSetu workflow."""

from google.adk.agents import SequentialAgent

root_agent = SequentialAgent(
    name="vyaparsetu",
    description="VyaparSetu autonomous supplier invoice-to-safe-payment decision agent.",
    sub_agents=[],
)

