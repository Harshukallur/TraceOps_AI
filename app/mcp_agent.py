
import asyncio
import json
import re
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

FalkorDB evidence collected through MCP is the source of truth.

RULES
- Use only facts supported by supplied evidence.
- Never invent services, relationships, owners, incidents, deployments,
  runbooks, timestamps, causes, metrics, or remediation results.
- Report recorded service status exactly.
- A -> B means A depends on B.
- Preserve dependency direction exactly.
- Dependency paths indicate possible impact, not proof of an outage.
- Do not claim a service is failing without evidence.
- A deployment linked to an incident does not prove causation.
- Present unverified causes as hypotheses.
- Recommendations are not completed actions.
- Identify owners and runbooks only from returned evidence.
- State evidence limitations accurately.
- Do not claim to have performed actions.
- Do not describe a dependency relationship in the opposite direction.
- If evidence is insufficient for a report section, say so briefly.

Use these sections:

## 1. Executive Summary
## 2. Service Health
## 3. Dependency Impact
## 4. Related Incidents and Severity
## 5. Owning Team
## 6. Available Runbooks
## 7. Deployment–Incident Correlation
## 8. Recommended Investigation Steps
- Suggest evidence-based diagnostic actions.
- Compare deployment changes and timestamps with incident records
  and available service-health evidence.
- Do not state or imply that a deployment caused an incident unless
  the evidence confirms causation.
## 9. Evidence Limitations

Be concise, technical, and useful to an on-call engineer.
Never fabricate facts to fill a report section.
"""


def parse_tool_results(evidence):
    """Parse JSON tool results while preserving plain-text results."""
    parsed_results = {}

    for entry in evidence:
        tool_name = entry.get("tool", "unknown")
        parsed_items = []

        if entry.get("is_error", False):
            parsed_results[tool_name] = parsed_items
            continue

        raw_result = entry.get("result", [])

        if isinstance(raw_result, str):
            raw_result = [raw_result]

        if not isinstance(raw_result, list):
            parsed_results[tool_name] = [raw_result]
            continue

        for raw in raw_result:
            if not isinstance(raw, str):
                parsed_items.append(raw)
                continue

            if not raw.strip():
                continue

            try:
                parsed_items.append(json.loads(raw))
            except (json.JSONDecodeError, TypeError):
                parsed_items.append(raw.strip())

        parsed_results[tool_name] = parsed_items

    return parsed_results


def _extract_dependency_paths(evidence):
    """Return valid, unique dependency paths from MCP results."""
    parsed = parse_tool_results(evidence)
    paths = []
    seen = set()

    for item in parsed.get("find_dependencies", []):
        if not isinstance(item, dict):
            continue

        path = item.get("dependency_path")

        if (
            isinstance(path, list)
            and len(path) >= 2
            and all(
                isinstance(node, str) and node.strip()
                for node in path
            )
        ):
            path = [node.strip() for node in path]
            key = tuple(node.casefold() for node in path)

            if key not in seen:
                seen.add(key)
                paths.append(path)

    return paths


def _get_service_details(evidence):
    """Return the first valid service-details record."""
    parsed = parse_tool_results(evidence)

    for item in parsed.get("get_service_details", []):
        if (
            isinstance(item, dict)
            and item.get("name")
            and not item.get("error")
        ):
            return item

    return {}


def _get_first_owner(evidence):
    """Extract the recorded owning team."""
    parsed = parse_tool_results(evidence)

    for item in parsed.get("get_service_owner", []):
        if isinstance(item, str) and item.strip():
            return item.strip()

        if isinstance(item, dict):
            owner = item.get("name") or item.get("team")

            if owner:
                return str(owner).strip()

    return None


def _get_incidents(evidence):
    """Extract incident records returned by MCP."""
    parsed = parse_tool_results(evidence)

    return [
        item
        for item in parsed.get("get_related_incidents", [])
        if isinstance(item, dict) and not item.get("error")
    ]


def _get_runbooks(evidence):
    """Extract runbook records returned by MCP."""
    parsed = parse_tool_results(evidence)

    return [
        item
        for item in parsed.get("get_service_runbooks", [])
        if isinstance(item, dict) and not item.get("error")
    ]


def _get_deployment_correlations(evidence):
    """Extract deployment–incident correlations from MCP results."""
    parsed = parse_tool_results(evidence)
    correlations = []

    for item in parsed.get(
        "get_incident_deployment_correlations", []
    ):
        if not isinstance(item, dict) or item.get("error"):
            continue

        correlations.append({
            "deployment_id": item.get("deployment_id"),
            "deployment_version": item.get("deployment_version"),
            "deployment_status": item.get("deployment_status"),
            "deployment_description": item.get(
                "deployment_description"
            ),
            "incident_id": item.get("incident_id"),
            "incident_title": item.get("incident_title"),
            "incident_severity": item.get("incident_severity"),
            "incident_status": item.get("incident_status"),
            "service_name": item.get("service_name"),
            "service_status": item.get("service_status"),
            "relationship": item.get("relationship"),
            "causation_confirmed": False,
        })

    return correlations


def build_evidence_summary(evidence):
    """Build a structured summary from actual MCP results."""
    summary = {
        "confirmed_facts": [],
        "dependency_paths": [],
        "potential_impact": [],
        "evidence_limitations": [],
        "deployment_correlations": [],
    }

    for entry in evidence:
        if entry.get("is_error", False):
            summary["evidence_limitations"].append(
                f"{entry.get('tool', 'Unknown tool')} returned an error."
            )

    details = _get_service_details(evidence)

    if not details:
        summary["evidence_limitations"].append(
            "No valid service details were returned."
        )
    else:
        summary["confirmed_facts"].append(
            f"Service name: {details['name']}"
        )

        if details.get("status"):
            summary["confirmed_facts"].append(
                f"Recorded service status: {details['status']}"
            )

    paths = _extract_dependency_paths(evidence)
    summary["dependency_paths"] = paths

    for path in paths:
        summary["potential_impact"].append({
            "path": path,
            "interpretation": (
                f"{path[0]} depends on "
                + " which depends on ".join(path[1:])
                + ". This indicates potential impact, not a confirmed outage."
            ),
        })

    if not paths:
        summary["evidence_limitations"].append(
            "No valid dependency paths were returned."
        )

    owner = _get_first_owner(evidence)

    if owner:
        summary["confirmed_facts"].append(
            f"Recorded owning team: {owner}"
        )

    incidents = _get_incidents(evidence)

    for incident in incidents:
        facts = [
            f"{key}: {incident[key]}"
            for key in ("id", "title", "severity", "status")
            if incident.get(key)
        ]

        if facts:
            summary["confirmed_facts"].append(
                "Related incident: " + "; ".join(facts)
            )

    if incidents:
        summary["evidence_limitations"].append(
            "Incident records do not independently establish root cause."
        )

    for runbook in _get_runbooks(evidence):
        facts = [
            f"{key}: {runbook[key]}"
            for key in ("id", "title", "instructions")
            if runbook.get(key)
        ]

        if facts:
            summary["confirmed_facts"].append(
                "Runbook: " + "; ".join(facts)
            )

    correlations = _get_deployment_correlations(evidence)
    summary["deployment_correlations"] = correlations

    for item in correlations:
        summary["confirmed_facts"].append(
            f"Deployment {item.get('deployment_id')} "
            f"(version {item.get('deployment_version')}) is linked "
            f"to incident {item.get('incident_id')} "
            f"({item.get('incident_title')}) through the recorded "
            f"{item.get('relationship')} relationship."
        )

    if correlations:
        summary["evidence_limitations"].append(
            "Deployment–incident links establish recorded relationships, "
            "not proof that a deployment caused an incident."
        )
    else:
        summary["evidence_limitations"].append(
            "No deployment–incident correlations were returned "
            "by the MCP tool."
        )

    summary["evidence_limitations"].append(
        "Actual error-rate measurements are unavailable unless explicitly "
        "returned by the supplied tools."
    )

    return summary


def build_deterministic_summary(service_name, evidence):
    """Build the executive summary from recorded graph evidence."""
    details = _get_service_details(evidence)
    owner = _get_first_owner(evidence)
    incidents = _get_incidents(evidence)
    paths = _extract_dependency_paths(evidence)

    sentences = []
    status = details.get("status")

    if status:
        sentences.append(f"{service_name} is recorded as {status}.")
    else:
        sentences.append(
            f"The current status of {service_name} was not returned."
        )

    if owner:
        sentences.append(f"The recorded owning team is {owner}.")

    if incidents:
        incident_ids = [
            str(item.get("id", "Unknown ID"))
            for item in incidents
        ]
        sentences.append(
            "Related incident records: " + ", ".join(incident_ids) + "."
        )
    else:
        sentences.append(
            "No related incident records were returned by the tool."
        )

    impacted_services = []

    for path in paths:
        for node in path[:-1]:
            if (
                node.casefold() != service_name.casefold()
                and node not in impacted_services
            ):
                impacted_services.append(node)

    if impacted_services:
        sentences.append(
            "Dependency paths identify these potentially affected services: "
            + ", ".join(impacted_services)
            + ". This indicates potential impact, not a confirmed outage."
        )

    return "## 1. Executive Summary\n\n" + " ".join(sentences)


def build_deterministic_dependency_section(evidence):
    """Build dependency impact directly from FalkorDB paths."""
    paths = _extract_dependency_paths(evidence)

    lines = [
        "## 3. Dependency Impact",
        "",
        (
            "The paths below were returned by FalkorDB. Each arrow means "
            "the service on the left depends on the service on the right."
        ),
        "",
    ]

    if not paths:
        lines.append(
            "No dependency paths were returned. Dependency impact cannot "
            "be determined from the available evidence."
        )
        return "\n".join(lines)

    for path in paths:
        lines.append(f"- {' -> '.join(path)}")

    seen_edges = set()
    relationship_lines = []

    for path in paths:
        for index in range(len(path) - 1):
            dependent = path[index]
            dependency = path[index + 1]
            edge = (dependent.casefold(), dependency.casefold())

            if edge not in seen_edges:
                seen_edges.add(edge)
                relationship_lines.append(
                    f"- {dependent} depends on {dependency}."
                )

    lines.extend(["", *relationship_lines, ""])
    lines.append(
        "Potential impact: upstream services in these paths may be affected "
        "if a downstream dependency is impaired. The paths do not prove "
        "that any other service is down."
    )

    return "\n".join(lines)


def build_deterministic_correlation_section(evidence):
    """Build deployment–incident correlation from MCP evidence only."""
    correlations = _get_deployment_correlations(evidence)

    lines = [
        "## 7. Deployment–Incident Correlation",
        "",
    ]

    if not correlations:
        lines.extend([
            "No deployment–incident correlations were returned "
            "by the MCP tool.",
            "",
            "A deployment-related root cause cannot be established "
            "from the available correlation evidence.",
        ])
        return "\n".join(lines)

    for item in correlations:
        deployment_id = item.get("deployment_id") or "Not provided"
        version = item.get("deployment_version") or "Not provided"
        deployment_status = (
            item.get("deployment_status") or "Not provided"
        )
        description = (
            item.get("deployment_description") or "Not provided"
        )
        incident_id = item.get("incident_id") or "Not provided"
        incident_title = item.get("incident_title") or "Not provided"
        severity = item.get("incident_severity") or "Not provided"
        incident_status = item.get("incident_status") or "Not provided"
        service_name = item.get("service_name") or "Not provided"
        relationship = item.get("relationship") or "Not provided"

        lines.extend([
            f"### Deployment {deployment_id}",
            f"- Service: {service_name}",
            f"- Version: {version}",
            f"- Deployment status: {deployment_status}",
            f"- Description: {description}",
            f"- Linked incident: {incident_id} ({incident_title})",
            f"- Incident severity: {severity}",
            f"- Incident status: {incident_status}",
            f"- Recorded relationship: {relationship}",
            "",
        ])

    lines.extend([
        "**Interpretation:** The graph records a relationship between "
        "the deployment and incident. This relationship does not prove "
        "that the deployment caused the incident.",
        "",
        "**Recommended investigation:** Compare the deployment changes "
        "with the incident timeline and inspect available error-rate "
        "and service-health evidence before drawing a causal conclusion.",
    ])

    return "\n".join(lines)


def replace_report_section(report, section_number, replacement):
    """Replace a numbered Markdown section or append it if missing."""
    pattern = (
        rf"(?ms)^##\s*{section_number}\.\s+.*?"
        rf"(?=^##\s*\d+\.\s+|\Z)"
    )

    if re.search(pattern, report):
        return re.sub(
            pattern,
            replacement.strip() + "\n\n",
            report,
            count=1,
        ).strip()

    return report.rstrip() + "\n\n" + replacement.strip()


def _normalize_text(text):
    """Normalize text for case-insensitive comparisons."""
    text = str(text).lower()

    replacements = {
        "â†’": "->",
        "âŸ¶": "->",
        "→": "->",
        "⟶": "->",
        "⟹": "->",
        "—>": "->",
        "–>": "->",
        "-->": "->",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return " ".join(text.split())


def _contains_entity(text, entity):
    """Match an entity as a phrase, not a partial word."""
    entity = _normalize_text(entity)

    if not entity:
        return False

    pattern = r"(?<!\w)" + re.escape(entity) + r"(?!\w)"
    return re.search(pattern, text) is not None


def _natural_language_reversal_warnings(report, dependency_paths):
    """Detect common reversed dependency statements."""
    normalized_report = _normalize_text(report)
    warnings = []

    def add_warning(message):
        if message not in warnings:
            warnings.append(message)

    for path in dependency_paths:
        for index in range(len(path) - 1):
            dependent = _normalize_text(path[index])
            dependency = _normalize_text(path[index + 1])

            reversed_patterns = [
                rf"{re.escape(dependency)}\s+depends\s+on\s+(?:the\s+)?{re.escape(dependent)}",
                rf"{re.escape(dependency)}\s+is\s+dependent\s+on\s+(?:the\s+)?{re.escape(dependent)}",
                rf"{re.escape(dependency)}\s+relies\s+on\s+(?:the\s+)?{re.escape(dependent)}",
                rf"{re.escape(dependency)}\s+relies\s+upon\s+(?:the\s+)?{re.escape(dependent)}",
                rf"{re.escape(dependency)}\s+requires\s+(?:the\s+)?{re.escape(dependent)}",
                rf"{re.escape(dependency)}\s+uses\s+(?:the\s+)?{re.escape(dependent)}",
            ]

            if any(
                re.search(pattern, normalized_report)
                for pattern in reversed_patterns
            ):
                add_warning(
                    f"Possible reversed dependency claim: the report says "
                    f"'{path[index + 1]}' depends on '{path[index]}', but "
                    f"graph evidence says '{path[index]}' depends on "
                    f"'{path[index + 1]}'."
                )

            generic_patterns = [
                rf"\bthe service\s+depends\s+on\s+(?:the\s+)?{re.escape(dependent)}\b",
                rf"\bthe service\s+is\s+dependent\s+on\s+(?:the\s+)?{re.escape(dependent)}\b",
                rf"\bthe service\s+relies\s+on\s+(?:the\s+)?{re.escape(dependent)}\b",
                rf"\bthe service\s+relies\s+upon\s+(?:the\s+)?{re.escape(dependent)}\b",
            ]

            if any(
                re.search(pattern, normalized_report)
                for pattern in generic_patterns
            ):
                add_warning(
                    "Possible reversed dependency claim involving "
                    f"'{path[index]} -> {path[index + 1]}'. "
                    "Verify the sentence against the graph."
                )

    return warnings


def _has_explicit_causal_negation(text, match_start):
    """
    Check whether a causal phrase is explicitly denied in its sentence.

    This is a heuristic. It is deliberately limited to common negations
    such as 'does not prove that the deployment caused the incident'.
    """
    sentence_start = max(
        text.rfind(".", 0, match_start),
        text.rfind("!", 0, match_start),
        text.rfind("?", 0, match_start),
        text.rfind("\n", 0, match_start),
    ) + 1

    preceding_text = text[sentence_start:match_start]

    negation_patterns = [
        r"\bdoes not prove that\s+(?:the\s+)?$",
        r"\bdoes not establish that\s+(?:the\s+)?$",
        r"\bdoes not confirm that\s+(?:the\s+)?$",
        r"\bcannot prove that\s+(?:the\s+)?$",
        r"\bcannot establish that\s+(?:the\s+)?$",
        r"\bcannot confirm that\s+(?:the\s+)?$",
        r"\bdoesn't prove that\s+(?:the\s+)?$",
        r"\bdoesn't establish that\s+(?:the\s+)?$",
        r"\bdoesn't confirm that\s+(?:the\s+)?$",
        r"\bnot proven that\s+(?:the\s+)?$",
        r"\bnot confirmed that\s+(?:the\s+)?$",
        r"\bnot established that\s+(?:the\s+)?$",
        r"\bno evidence that\s+(?:the\s+)?$",
        r"\bthere is no evidence that\s+(?:the\s+)?$",
        r"\bhas not been shown that\s+(?:the\s+)?$",
        r"\bhas not been established that\s+(?:the\s+)?$",
    ]

    return any(
        re.search(pattern, preceding_text)
        for pattern in negation_patterns
    )


def validate_report(report, evidence, service_name):
    """
    Check selected report claims against MCP evidence.

    These checks detect selected inconsistencies but cannot guarantee
    that every statement is correct.
    """
    warnings = []
    report_lower = _normalize_text(report)

    def add_warning(message):
        if message not in warnings:
            warnings.append(message)

    if not _contains_entity(report_lower, service_name):
        add_warning(
            f"Report does not mention investigated service '{service_name}'."
        )

    details = _get_service_details(evidence)
    recorded_status = details.get("status")

    if (
        recorded_status
        and _normalize_text(recorded_status) not in report_lower
    ):
        add_warning(
            f"Recorded status '{recorded_status}' is missing from the report."
        )

    owner = _get_first_owner(evidence)

    if owner and owner.lower() not in ("none", "null", "unknown"):
        if not _contains_entity(report_lower, owner):
            add_warning(
                f"Recorded owner '{owner}' is missing from the report."
            )

    paths = _extract_dependency_paths(evidence)

    for path in paths:
        expected = _normalize_text(" -> ".join(path))
        reversed_path = _normalize_text(" -> ".join(reversed(path)))

        if expected not in report_lower and reversed_path in report_lower:
            add_warning(
                "Dependency direction appears reversed: "
                + " -> ".join(path)
                + ". The report contains the reverse path."
            )

    for warning in _natural_language_reversal_warnings(report, paths):
        add_warning(warning)

    correlations = _get_deployment_correlations(evidence)

    for item in correlations:
        deployment_id = item.get("deployment_id")
        incident_id = item.get("incident_id")

        if deployment_id and not _contains_entity(
            report_lower, deployment_id
        ):
            add_warning(
                f"Recorded deployment '{deployment_id}' "
                "is missing from the report."
            )

        if incident_id and not _contains_entity(
            report_lower, incident_id
        ):
            add_warning(
                f"Linked incident '{incident_id}' is missing from the report."
            )

    # Detect possible affirmative causal claims.
    # Explicit denials are ignored, but positive claims still warn.
    causal_patterns = [
        r"\bthe deployment caused\b",
        r"\bdeployment caused the incident\b",
        r"\bcaused by the deployment\b",
        r"\bthe root cause (?:is|was)\b",
        r"\broot cause has been identified as\b",
    ]

    for pattern in causal_patterns:
        for match in re.finditer(pattern, report_lower):
            if _has_explicit_causal_negation(
                report_lower, match.start()
            ):
                continue

            add_warning(
                "The report contains a possible causal or root-cause claim. "
                "Verify that the evidence supports it."
            )
            break

    return warnings


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
    data = response.json()
    assistant_message = data.get("message", {})

    if not isinstance(assistant_message, dict):
        raise RuntimeError(
            "Ollama returned an unexpected response format."
        )

    return assistant_message


async def investigate(service_name: str) -> dict:
    """Collect MCP evidence, generate the report, and validate it."""
    service_name = service_name.strip()

    if not service_name:
        raise ValueError("Please provide a valid service name.")

    if not PYTHON_EXE.exists():
        raise FileNotFoundError(
            f"Project virtual-environment Python was not found: {PYTHON_EXE}"
        )

    server_params = StdioServerParameters(
        command=str(PYTHON_EXE),
        args=["-m", "app.mcp_server"],
        cwd=str(PROJECT_ROOT),
    )

    async with stdio_client(server_params) as (
        read_stream,
        write_stream,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            available_tools = await session.list_tools()
            available_names = {
                tool.name for tool in available_tools.tools
            }

            required_tools = [
                "get_service_details",
                "find_dependencies",
                "get_service_owner",
                "get_related_incidents",
                "get_service_runbooks",
                "get_incident_deployment_correlations",
            ]

            missing_tools = [
                name for name in required_tools
                if name not in available_names
            ]

            if missing_tools:
                raise RuntimeError(
                    f"MCP server is missing required tools: {missing_tools}"
                )

            evidence = []

            for tool_name in required_tools:
                arguments = {"service_name": service_name}
                result = await session.call_tool(tool_name, arguments)

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

            service_details = _get_service_details(evidence)

            if not service_details:
                return {
                    "service_name": service_name,
                    "status": "not_found",
                    "report": (
                        f"No valid service details were found for "
                        f"'{service_name}'. Check the service name "
                        "and the FalkorDB graph."
                    ),
                    "evidence": evidence,
                    "validation_warnings": [],
                }

            evidence_summary = build_evidence_summary(evidence)

            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Write an investigation report for '{service_name}'.\n\n"
                        "Use only the evidence below. Preserve dependency "
                        "directions exactly. For every edge A -> B, state "
                        "that A depends on B, not the reverse. Treat impact "
                        "as potential unless an outage is explicitly recorded. "
                        "Do not claim an unverified cause or completed action.\n\n"
                        "STRUCTURED EVIDENCE SUMMARY:\n"
                        f"{json.dumps(evidence_summary, indent=2)}\n\n"
                        "RAW MCP EVIDENCE:\n"
                        f"{json.dumps(evidence, indent=2, default=str)}"
                    ),
                },
            ]

            assistant_message = ask_qwen(messages)
            report = assistant_message.get("content", "").strip()

            if not report:
                raise RuntimeError(
                    "The local model returned an empty report."
                )

            # Replace critical sections with evidence-based content.
            report = replace_report_section(
                report,
                1,
                build_deterministic_summary(service_name, evidence),
            )

            report = replace_report_section(
                report,
                3,
                build_deterministic_dependency_section(evidence),
            )

            report = replace_report_section(
                report,
                7,
                build_deterministic_correlation_section(evidence),
            )

            validation_warnings = validate_report(
                report,
                evidence,
                service_name,
            )

            return {
                "service_name": service_name,
                "status": "ok",
                "report": report,
                "evidence": evidence,
                "validation_warnings": validation_warnings,
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

        print("\n=== VALIDATION WARNINGS ===\n")
        warnings = result.get("validation_warnings", [])

        if warnings:
            for number, warning in enumerate(warnings, start=1):
                print(f"{number}. {warning}")
        else:
            print("No issues detected by the basic validation checks.")

        print("\n=== MCP EVIDENCE ===\n")
        print(json.dumps(result["evidence"], indent=2, default=str))

    except Exception as exc:
        raise SystemExit(f"Investigation failed: {exc}") from exc
