
import os

from dotenv import load_dotenv
from falkordb import FalkorDB

load_dotenv()


def get_graph():
    """Return the TraceOps FalkorDB graph connection."""
    host = os.getenv("FALKORDB_HOST", "127.0.0.1")
    port = int(os.getenv("FALKORDB_PORT", "6379"))
    graph_name = os.getenv("FALKORDB_GRAPH", "traceops")

    db = FalkorDB(host=host, port=port)
    return db.select_graph(graph_name)
