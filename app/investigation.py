
from graph.queries import (
    find_service_by_name,
    find_affected_services,
    find_service_owner,
    find_service_incidents,
    find_service_runbooks,
)


def investigate_service(service_name: str) -> dict:
    """
    Collect graph evidence for an incident investigation.
    Validate the service before running the investigation.
    """
    service_name = service_name.strip()

    if not service_name:
        raise ValueError("Please enter a service name.")

    canonical_name = find_service_by_name(service_name)

    if canonical_name is None:
        raise ValueError(
            f"Service '{service_name}' was not found in FalkorDB. "
            "Please check the service name and try again."
        )

    affected_services = find_affected_services(canonical_name)
    owners = find_service_owner(canonical_name)
    incidents = find_service_incidents(canonical_name)
    runbooks = find_service_runbooks(canonical_name)

    return {
        "service": canonical_name,
        "potentially_affected_services": affected_services,
        "owners": owners,
        "incidents": incidents,
        "runbooks": runbooks,
    }
