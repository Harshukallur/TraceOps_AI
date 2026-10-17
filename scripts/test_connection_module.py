
from graph.connection import get_graph


def main():
    graph = get_graph()

    result = graph.query("""
        RETURN 'TraceOps connection module works' AS message
    """)

    print(result.result_set[0][0])
    print("Connection module test passed.")


if __name__ == "__main__":
    main()
