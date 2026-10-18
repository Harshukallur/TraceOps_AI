
from mcp.server.fastmcp import FastMCP

from graph.queries import (
    find_affected_services,
    find_service_owner,
    find_service_incidents,
    find_service_runbooks,
    find_service_by_name,
    find_incident_deployment_correlations,
)
mcp = FastMCP("TraceOps AI Graph Tools")


@mcp.tool()
def get_service_details(service_name: str) -> dict:
    """Return the full properties of a service from FalkorDB."""
    details = find_service_by_name(service_name)

    if details is None:
        return {"error": f"Service '{service_name}' was not found."}

    return dict(details)


@mcp.tool()
def find_dependencies(service_name: str) -> list[dict]:
    """Find downstream services affected by a service, including dependency paths."""
    return find_affected_services(service_name)


@mcp.tool()
def get_service_owner(service_name: str) -> list[str]:
    """Find the team responsible for a service."""
    return find_service_owner(service_name)


@mcp.tool()
def get_related_incidents(service_name: str) -> list[dict]:
    """Find incidents connected to a service in FalkorDB."""
    return find_service_incidents(service_name)


@mcp.tool()
def get_service_runbooks(service_name: str) -> list[dict]:
    """Find runbooks connected to a service in FalkorDB."""
    return find_service_runbooks(service_name)

@mcp.tool()
def get_incident_deployment_correlations(service_name: str) -> list[dict]:
    """Find deployments linked to incidents for a service."""
    return find_incident_deployment_correlations(service_name)


if __name__ == "__main__":
    mcp.run(transport="stdio")
