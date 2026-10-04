"""Write the agent's LangGraph structure as a Mermaid diagram to docs/agent_graph.md.

    cd backend && .venv/bin/python -m scripts.export_agent_graph

GitHub, VS Code and many Markdown viewers render Mermaid; for the report, paste the
diagram into https://mermaid.live and export it as an image.
"""

from types import SimpleNamespace

from app.agents.graph import AgentGraph
from app.core.config import PROJECT_ROOT, get_settings
from app.rag.retrieval import RetrievalConfig


def main() -> None:
    # The graph's structure doesn't depend on the database or models, so dummies suffice
    ctx = SimpleNamespace(settings=get_settings(), retrieval=RetrievalConfig())
    diagram = AgentGraph(ctx, planner="rules", similar_import_limit=3, max_recoveries=1).mermaid()
    target = PROJECT_ROOT / "docs" / "agent_graph.md"
    target.write_text(
        "# Agent graph (generated)\n\n"
        "Generated from the code by `scripts/export_agent_graph.py`; do not edit by hand.\n"
        "Dashed arrows are conditional edges (decisions).\n\n"
        f"```mermaid\n{diagram}```\n"
    )
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
