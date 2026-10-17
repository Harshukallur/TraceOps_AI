
from pprint import pprint

from app.investigation import investigate_service


def main():
    report = investigate_service("Payment API")
    pprint(report, sort_dicts=False)


if __name__ == "__main__":
    main()
