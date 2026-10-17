
from falkordb import FalkorDB


def main():
    db = FalkorDB(host="127.0.0.1", port=6379)
    graph = db.select_graph("traceops")

    # Test 1: Find services that depend directly or indirectly on Payment API.
    print("\n1. SERVICES THAT MAY BE AFFECTED BY PAYMENT API")
    result = graph.query("""
        MATCH path =
            (affected:Service)-[:DEPENDS_ON*1..4]->
            (target:Service {name: 'Payment API'})
        RETURN affected.name AS service, length(path) AS hops
        ORDER BY hops
    """)

    for row in result.result_set:
        print(f"- {row[0]} (dependency hops: {row[1]})")

    # Test 2: Find the team that owns Payment API.
    print("\n2. PAYMENT API OWNER")
    result = graph.query("""
        MATCH
            (service:Service {name: 'Payment API'})-[:OWNED_BY]->
            (team:Team)
        RETURN team.name
    """)

    for row in result.result_set:
        print(f"- {row[0]}")

    # Test 3: Find incidents affecting Payment API.
    print("\n3. INCIDENTS AFFECTING PAYMENT API")
    result = graph.query("""
        MATCH
            (incident:Incident)-[:AFFECTED]->
            (service:Service {name: 'Payment API'})
        RETURN incident.id, incident.title,
               incident.severity, incident.status
    """)

    for row in result.result_set:
        print(
            f"- {row[0]}: {row[1]} "
            f"(severity: {row[2]}, status: {row[3]})"
        )

    # Test 4: Find the troubleshooting runbook for Payment API.
    print("\n4. PAYMENT API RUNBOOK")
    result = graph.query("""
        MATCH
            (service:Service {name: 'Payment API'})-[:HAS_RUNBOOK]->
            (runbook:Runbook)
        RETURN runbook.id, runbook.title, runbook.instructions
    """)

    for row in result.result_set:
        print(f"- {row[0]}: {row[1]}")
        print(f"  Instructions: {row[2]}")


if __name__ == "__main__":
    main()
