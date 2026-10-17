
from falkordb import FalkorDB


def main():
    db = FalkorDB(host="127.0.0.1", port=6379)
    graph = db.select_graph("traceops")

    # Make seeding repeatable: clear this project's graph before rebuilding it.
    graph.query("MATCH (n) DETACH DELETE n")

    # Create synthetic service nodes.
    graph.query("""
        CREATE
          (:Service {id: 'svc-payment', name: 'Payment API', status: 'degraded'}),
          (:Service {id: 'svc-checkout', name: 'Checkout', status: 'healthy'}),
          (:Service {id: 'svc-orders', name: 'Order Management', status: 'healthy'}),
          (:Service {id: 'svc-auth', name: 'Auth Service', status: 'healthy'}),
          (:Service {id: 'svc-notify', name: 'Notification Service', status: 'healthy'})
    """)

    # Create teams.
    graph.query("""
        CREATE
          (:Team {id: 'team-payments', name: 'Payment Platform'}),
          (:Team {id: 'team-commerce', name: 'Commerce Engineering'}),
          (:Team {id: 'team-identity', name: 'Identity Platform'})
    """)

    # Create incidents.
    graph.query("""
        CREATE
          (:Incident {
            id: 'INC-1045',
            title: 'Payment errors after deployment',
            severity: 'high',
            status: 'investigating'
          }),
          (:Incident {
            id: 'INC-1032',
            title: 'Authentication timeout',
            severity: 'medium',
            status: 'resolved'
          })
    """)

    # Create deployments.
    graph.query("""
        CREATE
          (:Deployment {
            id: 'DEP-208',
            version: 'v2.4.1',
            status: 'completed',
            description: 'Payment API release'
          })
    """)

    # Create runbooks.
    graph.query("""
        CREATE
          (:Runbook {
            id: 'RB-PAY-01',
            title: 'Payment API Troubleshooting',
            instructions: 'Check recent deployments, error rates, and authentication dependencies.'
          }),
          (:Runbook {
            id: 'RB-AUTH-01',
            title: 'Authentication Troubleshooting',
            instructions: 'Check authentication latency, service health, and timeout errors.'
          })
    """)

    # Connect services: A DEPENDS_ON B means A relies on B.
    graph.query("""
        MATCH
          (orders:Service {id: 'svc-orders'}),
          (checkout:Service {id: 'svc-checkout'}),
          (payment:Service {id: 'svc-payment'}),
          (auth:Service {id: 'svc-auth'}),
          (notify:Service {id: 'svc-notify'})
        CREATE
          (orders)-[:DEPENDS_ON]->(checkout),
          (checkout)-[:DEPENDS_ON]->(payment),
          (payment)-[:DEPENDS_ON]->(auth),
          (checkout)-[:DEPENDS_ON]->(notify)
    """)

    # Connect services to their owning teams.
    graph.query("""
        MATCH
          (payment:Service {id: 'svc-payment'}),
          (checkout:Service {id: 'svc-checkout'}),
          (orders:Service {id: 'svc-orders'}),
          (auth:Service {id: 'svc-auth'}),
          (payments_team:Team {id: 'team-payments'}),
          (commerce_team:Team {id: 'team-commerce'}),
          (identity_team:Team {id: 'team-identity'})
        CREATE
          (payment)-[:OWNED_BY]->(payments_team),
          (checkout)-[:OWNED_BY]->(commerce_team),
          (orders)-[:OWNED_BY]->(commerce_team),
          (auth)-[:OWNED_BY]->(identity_team)
    """)

    # Connect incidents to affected services.
    graph.query("""
        MATCH
          (payment:Service {id: 'svc-payment'}),
          (auth:Service {id: 'svc-auth'}),
          (incident1:Incident {id: 'INC-1045'}),
          (incident2:Incident {id: 'INC-1032'})
        CREATE
          (incident1)-[:AFFECTED]->(payment),
          (incident2)-[:AFFECTED]->(auth)
    """)

    # Connect deployment, incident, and runbooks.
    graph.query("""
        MATCH
          (deployment:Deployment {id: 'DEP-208'}),
          (payment:Service {id: 'svc-payment'}),
          (incident:Incident {id: 'INC-1045'}),
          (payment_runbook:Runbook {id: 'RB-PAY-01'}),
          (auth:Service {id: 'svc-auth'}),
          (auth_runbook:Runbook {id: 'RB-AUTH-01'})
        CREATE
          (deployment)-[:DEPLOYED_TO]->(payment),
          (deployment)-[:FOLLOWED_BY]->(incident),
          (payment)-[:HAS_RUNBOOK]->(payment_runbook),
          (auth)-[:HAS_RUNBOOK]->(auth_runbook)
    """)

    # Print counts so we can verify the graph.
    result = graph.query("""
        MATCH (n)
        RETURN labels(n)[0] AS node_type, count(*) AS total
        ORDER BY node_type
    """)

    print("TraceOps synthetic graph created.")
    print("\nNode counts:")

    for row in result.result_set:
        print(f"{row[0]}: {row[1]}")

    relationship_result = graph.query("""
        MATCH ()-[r]->()
        RETURN type(r) AS relationship_type, count(*) AS total
        ORDER BY relationship_type
    """)

    print("\nRelationship counts:")

    for row in relationship_result.result_set:
        print(f"{row[0]}: {row[1]}")


if __name__ == "__main__":
    main()
