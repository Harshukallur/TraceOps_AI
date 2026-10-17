
from app.investigation import investigate_service
from app.llm import ask_local_llm


def investigate_with_ai(service_name: str) -> dict:
    """Build a report from FalkorDB evidence and add local-LLM interpretation."""

    evidence = investigate_service(service_name)

    service = evidence["service"]
    affected = evidence.get("potentially_affected_services", [])
    owners = evidence.get("owners", [])
    incidents = evidence.get("incidents", [])
    runbooks = evidence.get("runbooks", [])

    # Generate a short interpretation using only the retrieved graph evidence.
    
    prompt = f"""
You are TraceOps AI, an evidence-grounded incident investigation assistant.

Explain the graph relationships in 2-3 sentences using only the supplied facts.

Target service: {service}
Potentially affected services and exact paths: {affected}
Owning teams: {owners}
Related incidents: {incidents}
Runbooks: {runbooks}

Strict rules:
- Do not diagnose the root cause or speculate about what is likely happening.
- Do not infer that a service is healthy, failing, down, or recovered.
- A resolved incident describes that incident's status; it does not prove
  the current service is healthy or explain a new failure.
- Describe downstream services as potentially affected, not confirmed impacted.
- Do not introduce facts absent from the evidence.
- If no root cause is established, explicitly say so.
- Return only 2-3 concise sentences.
"""

    try:
        ai_interpretation = ask_local_llm(prompt).strip()
    except Exception:
        # Keep the evidence report available if the local model is unavailable.
        ai_interpretation = (
            "The graph evidence identifies the service relationships and "
            "related operational records listed below. Dependency relationships "
            "alone do not confirm an outage."
        )

    # Build critical factual sections directly from graph evidence.
    report = [
        "## Executive Summary",
        f"Target service: **{service}**.",
    ]

    if incidents:
        report.append(
            "Related incidents: " + "; ".join(
                f'{i["id"]} — {i["title"]} '
                f'({i["severity"]}, {i["status"]})'
                for i in incidents
            ) + "."
        )
    else:
        report.append("No related incidents were identified in the graph evidence.")

    if owners:
        report.append("Owning team(s): " + ", ".join(owners) + ".")
    else:
        report.append("No owning team was identified in the graph evidence.")

    report.extend(["", "## AI Interpretation", ai_interpretation, "", "## Potential Impact"])

    if affected:
        for item in affected:
            path = " → ".join(item["dependency_path"])
            report.append(
                f'- **{item["service"]}** — Path: `{path}`; '
                f'{item["hops"]} hop(s). This service could be affected '
                f'if the dependency chain experiences a problem; an outage '
                f'is not confirmed by this relationship alone.'
            )
    else:
        report.append("No potentially affected services were identified in the graph evidence.")

    report.extend(["", "## Related Incident"])

    if incidents:
        for incident in incidents:
            report.append(
                f'- **{incident["id"]}** — {incident["title"]}; '
                f'severity: {incident["severity"]}; '
                f'status: {incident["status"]}.'
            )
    else:
        report.append("No related incident was identified in the graph evidence.")

    report.extend(["", "## Owning Team"])

    if owners:
        report.extend(f"- {owner}" for owner in owners)
    else:
        report.append("No owning team was identified in the graph evidence.")

    report.extend(["", "## Recommended Investigation Steps"])

    if runbooks:
        for runbook in runbooks:
            report.append(
                f'**{runbook["id"]} — {runbook["title"]}**'
            )
            report.append(runbook["instructions"])
    else:
        report.append("No troubleshooting runbook was identified in the graph evidence.")

    report.extend([
        "",
        "## Evidence Limitations",
        "Dependency relationships show potential impact, not confirmed outages. "
        "The root cause is not established unless explicitly supported by the "
        "available graph evidence.",
    ])

    return {
        "evidence": evidence,
        "ai_analysis": "\n".join(report),
        "ai_interpretation": ai_interpretation,
    }
