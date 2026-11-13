"""Entrypoint discovered by ADK and agents-cli."""

from google.adk.apps import App

from app.agents.root_orchestrator import root_agent as root_agent

app = App(root_agent=root_agent, name="app")
