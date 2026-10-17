from flask import Flask, jsonify, request
from flask_cors import CORS

from graph.queries import get_graph_visualization_data
from app.ai_investigator import investigate_with_ai

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://127.0.0.1:5173",
            ]
        }
    },
)


@app.get("/api/health")
def health():
    """Check whether the API can reach FalkorDB."""
    try:
        graph_data = get_graph_visualization_data()

        return jsonify({
            "status": "ok",
            "service": "TraceOps AI API",
            "graph_database": "connected",
            "nodes": len(graph_data["nodes"]),
            "relationships": len(graph_data["edges"]),
        }), 200

    except Exception:
        app.logger.exception("FalkorDB health check failed")

        return jsonify({
            "status": "error",
            "service": "TraceOps AI API",
            "graph_database": "unavailable",
        }), 503


@app.get("/api/graph")
def graph():
    """Return graph data for the frontend visualization."""
    try:
        data = get_graph_visualization_data()
        return jsonify(data), 200

    except Exception:
        app.logger.exception("Graph retrieval failed")

        return jsonify({
            "error": "Unable to retrieve graph data from FalkorDB."
        }), 503


@app.post("/api/investigate")
def investigate():
    """Investigate a service using FalkorDB evidence and local AI."""
    data = request.get_json(silent=True) or {}

    service_name = data.get("service_name")
    question = data.get("question", "")

    if not isinstance(service_name, str) or not service_name.strip():
        return jsonify({
            "error": "Please provide a valid service_name."
        }), 400

    if not isinstance(question, str):
        return jsonify({
            "error": "The question must be a string."
        }), 400

    try:
        result = investigate_with_ai(service_name.strip())

        if question.strip():
            result["investigation_question"] = question.strip()

        return jsonify(result), 200

    except Exception:
        app.logger.exception("Service investigation failed")

        return jsonify({
            "error": (
                "The investigation failed. Check the Flask terminal "
                "for details about FalkorDB or local AI."
            )
        }), 500


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True,
    )
