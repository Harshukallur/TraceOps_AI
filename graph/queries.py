
from graph.connection import get_graph


def find_affected_services(service_name: str) -> list[dict]:
    """Find dependent services and return their dependency paths."""
    graph = get_graph()
    service_name = service_name.strip()

    result = graph.query(
        """
        MATCH path =
            (affected:Service)-[:DEPENDS_ON*1..4]->
            (target:Service)
        WHERE toLower(target.name) = toLower($service_name)
        WITH affected, path
        RETURN affected.name AS service,
               length(path) AS hops,
               [node IN nodes(path) | node.name] AS dependency_path
        ORDER BY hops
        """,
        {"service_name": service_name},
    )

    return [
        {
            "service": row[0],
            "hops": row[1],
            "dependency_path": row[2],
        }
        for row in result.result_set
    ]


def find_service_owner(service_name: str) -> list[str]:
    """Find the teams that own a service."""
    graph = get_graph()
    service_name = service_name.strip()

    result = graph.query(
        """
        MATCH
            (service:Service)-[:OWNED_BY]->
            (team:Team)
        WHERE toLower(service.name) = toLower($service_name)
        RETURN team.name AS team
        """,
        {"service_name": service_name},
    )

    return [row[0] for row in result.result_set]


def find_service_incidents(service_name: str) -> list[dict]:
    """Find incidents directly linked to a service."""
    graph = get_graph()
    service_name = service_name.strip()

    result = graph.query(
        """
        MATCH
            (incident:Incident)-[:AFFECTED]->
            (service:Service)
        WHERE toLower(service.name) = toLower($service_name)
        RETURN incident.id AS id,
               incident.title AS title,
               incident.severity AS severity,
               incident.status AS status
        ORDER BY incident.id
        """,
        {"service_name": service_name},
    )

    return [
        {
            "id": row[0],
            "title": row[1],
            "severity": row[2],
            "status": row[3],
        }
        for row in result.result_set
    ]


def find_service_runbooks(service_name: str) -> list[dict]:
    """Find troubleshooting runbooks linked to a service."""
    graph = get_graph()
    service_name = service_name.strip()

    result = graph.query(
        """
        MATCH
            (service:Service)-[:HAS_RUNBOOK]->
            (runbook:Runbook)
        WHERE toLower(service.name) = toLower($service_name)
        RETURN runbook.id AS id,
               runbook.title AS title,
               runbook.instructions AS instructions
        ORDER BY runbook.id
        """,
        {"service_name": service_name},
    )

    return [
        {
            "id": row[0],
            "title": row[1],
            "instructions": row[2],
        }
        for row in result.result_set
    ]


def find_service_by_name(service_name: str) -> dict | None:
    """Return all properties of a service, ignoring letter case."""
    graph = get_graph()
    service_name = service_name.strip()

    result = graph.query(
        """
        MATCH (service:Service)
        WHERE toLower(service.name) = toLower($service_name)
        RETURN properties(service) AS details
        LIMIT 1
        """,
        {"service_name": service_name},
    )

    if not result.result_set:
        return None

    return result.result_set[0][0]


def get_graph_visualization_data() -> dict:
    """Retrieve graph nodes and relationships directly from FalkorDB."""
    graph = get_graph()

    result = graph.query(
        """
        MATCH (source)-[relationship]->(target)
        RETURN
            labels(source) AS source_labels,
            properties(source) AS source_properties,
            type(relationship) AS relationship_type,
            labels(target) AS target_labels,
            properties(target) AS target_properties
        """
    )

    nodes = {}
    edges = []

    for row in result.result_set:
        source_labels = row[0]
        source_properties = row[1]
        relationship_type = row[2]
        target_labels = row[3]
        target_properties = row[4]

        source_id = str(
            source_properties.get(
                "id",
                source_properties.get("name", str(source_properties)),
            )
        )
        target_id = str(
            target_properties.get(
                "id",
                target_properties.get("name", str(target_properties)),
            )
        )

        nodes[source_id] = {
            "id": source_id,
            "label": str(
                source_properties.get(
                    "name",
                    source_properties.get(
                        "title",
                        source_properties.get("id", source_id),
                    ),
                )
            ),
            "type": source_labels[0] if source_labels else "Node",
            "properties": source_properties,
        }

        nodes[target_id] = {
            "id": target_id,
            "label": str(
                target_properties.get(
                    "name",
                    target_properties.get(
                        "title",
                        target_properties.get("id", target_id),
                    ),
                )
            ),
            "type": target_labels[0] if target_labels else "Node",
            "properties": target_properties,
        }

        edges.append({
            "source": source_id,
            "target": target_id,
            "relationship": relationship_type,
        })

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
    }


def find_incident_deployment_correlations(
    service_name: str,
) -> list[dict]:
    """Find deployments linked to incidents for a given service."""
    graph = get_graph()
    service_name = service_name.strip()

    result = graph.query(
        """
        MATCH
            (deployment:Deployment)-[:FOLLOWED_BY]->
            (incident:Incident),
            (deployment)-[:DEPLOYED_TO]->
            (service:Service)
        WHERE toLower(service.name) = toLower($service_name)
        RETURN
            deployment.id AS deployment_id,
            deployment.version AS deployment_version,
            deployment.status AS deployment_status,
            deployment.description AS deployment_description,
            incident.id AS incident_id,
            incident.title AS incident_title,
            incident.severity AS incident_severity,
            incident.status AS incident_status,
            service.name AS service_name,
            service.status AS service_status
        ORDER BY deployment.id, incident.id
        """,
        {"service_name": service_name},
    )

    return [
        {
            "deployment_id": row[0],
            "deployment_version": row[1],
            "deployment_status": row[2],
            "deployment_description": row[3],
            "incident_id": row[4],
            "incident_title": row[5],
            "incident_severity": row[6],
            "incident_status": row[7],
            "service_name": row[8],
            "service_status": row[9],
            "relationship": "Deployment FOLLOWED_BY Incident",
            "causation_confirmed": False,
        }
        for row in result.result_set
    ]

