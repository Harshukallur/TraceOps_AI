
from app.investigation import investigate_service


def main():
    print("=" * 60)
    print("                  TraceOps AI")
    print("       Graph-Powered Incident Investigator")
    print("=" * 60)

    print("\nAvailable services:")
    print("- Payment API")
    print("- Checkout")
    print("- Order Management")
    print("- Auth Service")
    print("- Notification Service")

    service_name = input(
        "\nEnter the service to investigate: "
    ).strip()

    if not service_name:
        print("\nPlease enter a service name.")
        return

    try:
        report = investigate_service(service_name)
    except ValueError as exc:
        print(f"\nInvestigation failed: {exc}")
        return
    except Exception as exc:
        print(f"\nUnexpected investigation error: {exc}")
        return

    print("\n" + "=" * 60)
    print(f" INVESTIGATION REPORT: {report['service']}")
    print("=" * 60)

    print("\n1. POTENTIALLY AFFECTED SERVICES")
    affected = report["potentially_affected_services"]

    if affected:
        for item in affected:
            print(f"\n- {item['service']}")
            print(f"  Dependency hops: {item['hops']}")
            print(
                "  Evidence path: "
                + " -> ".join(item["dependency_path"])
            )
    else:
        print("- No dependent services found.")

    print("\n2. OWNING TEAMS")
    if report["owners"]:
        for owner in report["owners"]:
            print(f"- {owner}")
    else:
        print("- No owner found.")

    print("\n3. RELATED INCIDENTS")
    if report["incidents"]:
        for incident in report["incidents"]:
            print(f"- {incident['id']}: {incident['title']}")
            print(f"  Severity: {incident['severity']}")
            print(f"  Status: {incident['status']}")
    else:
        print("- No directly linked incidents found.")

    print("\n4. TROUBLESHOOTING RUNBOOKS")
    if report["runbooks"]:
        for runbook in report["runbooks"]:
            print(f"- {runbook['id']}: {runbook['title']}")
            print(f"  Instructions: {runbook['instructions']}")
    else:
        print("- No runbooks found.")

    print("\nIMPORTANT")
    print("Dependency paths indicate potential impact,")
    print("not confirmed outages. Verify service health")
    print("before taking corrective action.")


if __name__ == "__main__":
    main()
