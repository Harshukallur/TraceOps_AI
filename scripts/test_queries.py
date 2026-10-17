
from graph.queries import (
    find_affected_services,
    find_service_owner,
    find_service_incidents,
    find_service_runbooks,
)


def main():
    service = "Payment API"

    print("\nAffected services:")
    print(find_affected_services(service))

    print("\nOwners:")
    print(find_service_owner(service))

    print("\nIncidents:")
    print(find_service_incidents(service))

    print("\nRunbooks:")
    print(find_service_runbooks(service))


if __name__ == "__main__":
    main()
