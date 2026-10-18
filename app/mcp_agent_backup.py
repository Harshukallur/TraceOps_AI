
import asyncio
import json
from pathlib import Path

import requests
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:3b"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYTHON_EXE = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"



SYSTEM_PROMPT = """
You are TraceOps AI, a service reliability investigation agent.

Your task is to explain service reliability using evidence collected
from FalkorDB through MCP tools.

SOURCE OF TRUTH
- FalkorDB evidence is authoritative for stored graph facts.
- Use only facts supported by the supplied evidence.
- Never invent services, relationships, owners, incidents, deployments,
  runbooks, timestamps, causes, or remediation results.
- You may explain possible consequences, but label them as possibilities.

DEPENDENCY DIRECTION — CRITICAL
- Interpret each dependency path exactly in the direction provided.
- If the path is Checkout -> Payment API, explain:
  "Checkout depends on Payment API."
- If the path is Order Management -> Checkout -> Payment API, explain:
  "Order Management depends on Checkout, which depends on Payment API."
- A path returned by find_dependencies represents services that depend
  on the investigated service and may be affected by its failure.
- Do not reverse the path or describe these services as upstream
  dependencies of the investigated service.
- A dependency path indicates a potential impact, not proof that
  another service is failing.
- Do not claim a service is affected in production unless the evidence
  confirms that impact.

SERVICE HEALTH
- Report the exact status returned by the service details evidence.
- Do not infer a service's health from an incident or dependency alone.
- Do not invent health checks, metrics, or error rates.

INCIDENTS AND DEPLOYMENTS
- Report incident IDs, titles, severities, and statuses only when present.
- Report deployment IDs, versions, and descriptions only when present.
- A deployment occurring near an incident does not prove causation.
- Describe a deployment as a possible lead for investigation unless
  the evidence establishes a causal relationship.
- Never claim an incident is resolved unless the evidence says so.

OWNERS AND RUNBOOKS
- Identify the owning team only from returned ownership evidence.
- Recommend checks based on the actual runbook instructions supplied.
- Clearly distinguish a recommended check from an action already performed.
- Do not claim to have restarted, deployed, modified, or remediated anything.

MISSING OR INCOMPLETE EVIDENCE
- If a tool returns no results, state that no linked evidence was returned
  by that tool.
- Do not say evidence is missing if the supplied evidence contains it.
- Do not claim a query was performed when the supplied evidence does
  not show that it was performed.
- Mention limitations only when they are genuinely supported by the
  supplied evidence or by the scope of the available tools.

REPORT FORMAT

## 1. Executive Summary
Summarize the confirmed service condition and the main investigation lead.

## 2. Service Health
State the service name and reported status.

## 3. Dependency Impact
Explain dependency paths in their original direction.
Separate confirmed graph relationships from potential impact.
Never imply that a dependency path proves an outage.

## 4. Related Incidents and Severity
List linked incidents and their recorded severity and status.

## 5. Owning Team
State the recorded owner or say that no ownership evidence was returned.

## 6. Available Runbooks
List returned runbooks and their relevant instructions.

## 7. Recommended Investigation Steps
Provide prioritized, actionable checks grounded in the evidence.
Identify hypotheses as hypotheses and explain what should be verified.
Do not claim checks have already been performed.

## 8. Evidence Limitations
State only relevant limitations. Do not invent missing information.

WRITING RULES
- Be concise, technical, and useful to an on-call engineer.
- Do not fabricate facts to fill a report section.
- Use exact names and identifiers from the evidence.
- Never reveal hidden reasoning or claim certainty without evidence.
"""


def ask_qwen(messages):
    """Generate a report using the local Ollama model."""
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2},
        },
        timeout=300,
    )

    response.raise_for_status()
    return response.json()["message"]


async def investigate(service_name: str) -> dict:
    """
    Collect FalkorDB evidence using MCP and return a structured report.

    This function can be called by the Flask API or run from the terminal.
    """
    service_name = service_name.strip()

    if not service_name:
        raise ValueError("Please provide a valid service name.")

    server_params = StdioServerParameters(
        command=str(PYTHON_EXE),
        args=["-m", "app.mcp_server"],
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            available_tools = await session.list_tools()
            allowed_names = {
                tool.name for tool in available_tools.tools
            }

            # Call each required MCP tool once.
            required_tools = [
                "get_service_details",
                "find_dependencies",
                "get_service_owner",
                "get_related_incidents",
                "get_service_runbooks",
            ]

            missing_tools = [
                name for name in required_tools
                if name not in allowed_names
            ]

            if missing_tools:
                raise RuntimeError(
                    f"MCP server is missing required tools: {missing_tools}"
                )

            evidence = []

            for tool_name in required_tools:
                arguments = {"service_name": service_name}

                result = await session.call_tool(
                    tool_name,
                    arguments,
                )

                tool_result = [
                    item.text
                    for item in result.content
                    if hasattr(item, "text")
                ]

                evidence.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "is_error": result.isError,
                    "result": tool_result,
                })

            # Stop if the service lookup did not find the service.
            details_entry = next(
                item for item in evidence
                if item["tool"] == "get_service_details"
            )

            details_text = " ".join(details_entry["result"])

            if (
                details_entry["is_error"]
                or not details_entry["result"]
                or '"error"' in details_text.lower()
                or '"name"' not in details_text.lower()
            ):
                return {
                    "service_name": service_name,
                    "status": "not_found",
                    "report": (
                        f"No service details were found for "
                        f"'{service_name}'. Check the service name "
                        "and the FalkorDB graph."
                    ),
                    "evidence": evidence,
                }

            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Write an investigation report for '{service_name}'. "
                        "Use only this MCP evidence. Do not say upstream "
                        "dependencies were searched. Do not invent missing "
                        "evidence or completed actions.\n\n"
                        f"{json.dumps(evidence, indent=2, default=str)}"
                    ),
                },
            ]

            assistant_message = ask_qwen(messages)
            report = assistant_message.get("content", "").strip()

            if not report:
                raise RuntimeError("The local model returned an empty report.")

            # Return data to Flask instead of only printing it.
            return {
                "service_name": service_name,
                "status": "ok",
                "report": report,
                "evidence": evidence,
            }


if __name__ == "__main__":
    service = input(
        "Enter a service to investigate (e.g. Payment API): "
    ).strip()

    if not service:
        raise SystemExit("Please enter a service name.")

    try:
        result = asyncio.run(investigate(service))

        print("\n=== TRACEOPS AI INVESTIGATION ===\n")
        print(result["report"])

        print("\n=== MCP EVIDENCE ===\n")
        print(json.dumps(result["evidence"], indent=2, default=str))

    except Exception as exc:
        raise SystemExit(f"Investigation failed: {exc}") from exc
