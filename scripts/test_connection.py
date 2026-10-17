
from falkordb import FalkorDB


def main():
    # Connect to the FalkorDB container running on this computer.
    db = FalkorDB(host="127.0.0.1", port=6379)

    # Select (or create when first used) the TraceOps graph.
    graph = db.select_graph("traceops")

    # Run a small test query against FalkorDB.
    result = graph.query(
        "RETURN 'TraceOps connected to FalkorDB' AS message"
    )

    print(result.result_set[0][0])
    print("Database connection test passed.")


if __name__ == "__main__":
    main()
