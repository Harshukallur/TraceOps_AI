
import { useEffect, useRef, useState } from "react";
import cytoscape, {
  type Core,
  type ElementDefinition,
  type EventObject,
} from "cytoscape";

type GraphNode = {
  id: string;
  label: string;
  type: string;
  properties: Record<string, unknown>;
};

type GraphEdge = {
  source: string;
  target: string;
  relationship: string;
};

type GraphViewProps = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

const nodeColors: Record<string, string> = {
  Service: "#7767f5",
  Team: "#20bfa5",
  Incident: "#f06478",
  Deployment: "#e5a64b",
  Runbook: "#4799e8",
};

export default function GraphView({
  nodes,
  edges,
}: GraphViewProps) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  const [selectedNode, setSelectedNode] =
    useState<GraphNode | null>(null);
  const [search, setSearch] = useState("");
  const [activeType, setActiveType] = useState("All");

  useEffect(() => {
    const container = containerRef.current;

    if (!container) {
      return;
    }

    cyRef.current?.destroy();
    cyRef.current = null;

    if (nodes.length === 0) {
      return;
    }

    const nodeIds = new Set(nodes.map((node) => node.id));

    const elements: ElementDefinition[] = [
      ...nodes.map((node) => ({
        data: {
          id: node.id,
          label: node.label,
          type: node.type,
          status: String(
            node.properties.status ?? ""
          ).toLowerCase(),
          color: nodeColors[node.type] ?? "#8b95a7",
        },
      })),

      ...edges
        .filter(
          (edge) =>
            nodeIds.has(edge.source) &&
            nodeIds.has(edge.target)
        )
        .map((edge, index) => ({
          data: {
            id: `edge-${index}-${edge.source}-${edge.target}`,
            source: edge.source,
            target: edge.target,
            label: edge.relationship.replaceAll("_", " "),
            relationship: edge.relationship,
          },
        })),
    ];

    const cy = cytoscape({
      container,
      elements,
      minZoom: 0.2,
      maxZoom: 3,
      wheelSensitivity: 0.18,
      boxSelectionEnabled: false,

      layout: {
        name: "cose",
        animate: false,
        fit: true,
        padding: 60,
        nodeRepulsion: () => 12000,
        idealEdgeLength: () => 145,
        edgeElasticity: () => 80,
        gravity: 0.2,
        numIter: 700,
        randomize: true,
      },

      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "background-color": "data(color)",
            color: "#f8fafc",
            "font-size": 12,
            "font-weight": 600,
            "font-family": "Arial, sans-serif",
            "text-wrap": "wrap",
            "text-max-width": "120px",
            "text-valign": "center",
            "text-halign": "center",
            width: 84,
            height: 70,
            padding: "5px",
            "border-width": 2,
            "border-color": "#ffffff55",
            "text-outline-width": 2,
            "text-outline-color": "#111827",
            "min-zoomed-font-size": 8,
            "z-index": 10,
          },
        },

        {
          selector: 'node[type = "Service"]',
          style: {
            shape: "round-rectangle",
            width: 112,
            height: 66,
          },
        },

        {
          selector: 'node[type = "Team"]',
          style: {
            shape: "ellipse",
            width: 92,
            height: 82,
          },
        },

        {
          selector: 'node[type = "Incident"]',
          style: {
            shape: "round-rectangle",
            width: 126,
            height: 70,
            "border-width": 3,
            "border-color": "#ffbd69",
            "font-size": 11,
          },
        },

        {
          selector: 'node[type = "Deployment"]',
          style: {
            shape: "hexagon",
            width: 104,
            height: 72,
          },
        },

        {
          selector: 'node[type = "Runbook"]',
          style: {
            shape: "round-rectangle",
            width: 124,
            height: 68,
            "border-style": "dashed",
            "border-color": "#8ac8ff",
          },
        },

        {
          selector: 'node[status = "degraded"]',
          style: {
            "background-color": "#e44f67",
            "border-color": "#ffd0d7",
            "border-width": 4,
            width: 116,
            height: 74,
          },
        },

        {
          selector: 'node[status = "investigating"]',
          style: {
            "border-color": "#ffbd69",
            "border-width": 4,
          },
        },

        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#71829e",
            "target-arrow-color": "#b9c7dc",
            "target-arrow-shape": "triangle",
            "arrow-scale": 1.1,
            "curve-style": "bezier",
            label: "data(label)",
            color: "#e0e7f3",
            "font-size": 9,
            "font-weight": 600,
            "font-family": "Arial, sans-serif",
            "text-rotation": "autorotate",
            "text-background-color": "#111827",
            "text-background-opacity": 0.95,
            "text-background-padding": "3px",
            "min-zoomed-font-size": 8,
          },
        },

        {
          selector: ".dimmed",
          style: {
            opacity: 0.16,
          },
        },

        {
          selector: ".highlighted",
          style: {
            opacity: 1,
            "line-color": "#a99aff",
            "target-arrow-color": "#a99aff",
            width: 3,
          },
        },

        {
          selector: "node:selected",
          style: {
            "border-color": "#ffffff",
            "border-width": 4,
            "overlay-color": "#a99aff",
            "overlay-opacity": 0.18,
          },
        },
      ],
    });

    cyRef.current = cy;

    // Select a node and highlight its immediate connections.
    cy.on("tap", "node", (event: EventObject) => {
      const id = String(event.target.id());
      const found = nodes.find((node) => node.id === id);

      if (!found) {
        return;
      }

      setSelectedNode(found);

      cy.elements()
        .removeClass("highlighted")
        .addClass("dimmed");

      event.target
        .closedNeighborhood()
        .removeClass("dimmed")
        .addClass("highlighted");

      event.target.removeClass("dimmed");
    });

    // Clear selection when the graph background is clicked.
    cy.on("tap", (event: EventObject) => {
      if (event.target === cy) {
        setSelectedNode(null);
        cy.elements().removeClass("dimmed highlighted");
      }
    });

    cy.one("layoutstop", () => {
      if (!cy.destroyed()) {
        cy.resize();
        cy.fit(cy.elements(), 60);
      }
    });

    const resizeObserver = new ResizeObserver(() => {
      if (!cy.destroyed()) {
        cy.resize();
      }
    });

    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      cyRef.current = null;
      cy.destroy();
    };
  }, [nodes, edges]);

  // Filter visible nodes and relationships.
  useEffect(() => {
    const cy = cyRef.current;

    if (!cy || cy.destroyed()) {
      return;
    }

    const query = search.trim().toLowerCase();

    cy.batch(() => {
      cy.nodes().forEach((node) => {
        const label = String(
          node.data("label") ?? ""
        ).toLowerCase();

        const type = String(node.data("type") ?? "");

        const matchesSearch =
          !query || label.includes(query);

        const matchesType =
          activeType === "All" || type === activeType;

        node.style(
          "display",
          matchesSearch && matchesType
            ? "element"
            : "none"
        );
      });

      cy.edges().forEach((edge) => {
        const sourceVisible =
          edge.source().style("display") !== "none";

        const targetVisible =
          edge.target().style("display") !== "none";

        edge.style(
          "display",
          sourceVisible && targetVisible
            ? "element"
            : "none"
        );
      });
    });
  }, [search, activeType, nodes, edges]);

  function fitGraph() {
    const cy = cyRef.current;

    if (cy && !cy.destroyed()) {
      cy.fit(cy.elements(":visible"), 55);
      cy.center();
    }
  }

  function zoomIn() {
    const cy = cyRef.current;

    if (cy && !cy.destroyed()) {
      cy.zoom({
        level: Math.min(
          cy.zoom() * 1.2,
          cy.maxZoom()
        ),
        renderedPosition: {
          x: cy.width() / 2,
          y: cy.height() / 2,
        },
      });
    }
  }

  function zoomOut() {
    const cy = cyRef.current;

    if (cy && !cy.destroyed()) {
      cy.zoom({
        level: Math.max(
          cy.zoom() / 1.2,
          cy.minZoom()
        ),
        renderedPosition: {
          x: cy.width() / 2,
          y: cy.height() / 2,
        },
      });
    }
  }

  function clearSelection() {
    setSelectedNode(null);

    const cy = cyRef.current;

    if (cy && !cy.destroyed()) {
      cy.elements().removeClass("dimmed highlighted");
    }
  }

  return (
    <div
      style={{
        width: "100%",
        minWidth: 0,
        color: "#e5e7eb",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: 10,
          alignItems: "center",
          flexWrap: "wrap",
          marginBottom: 12,
        }}
      >
        <input
          aria-label="Search graph nodes"
          placeholder="Search services, teams, incidents..."
          value={search}
          onChange={(event) =>
            setSearch(event.target.value)
          }
          style={{
            flex: "1 1 220px",
            minWidth: 180,
            padding: "10px 12px",
            color: "#f8fafc",
            background: "#111827",
            border: "1px solid #334155",
            borderRadius: 8,
          }}
        />

        <select
          aria-label="Filter graph by node type"
          value={activeType}
          onChange={(event) =>
            setActiveType(event.target.value)
          }
          style={{
            padding: "10px 12px",
            color: "#f8fafc",
            background: "#111827",
            border: "1px solid #334155",
            borderRadius: 8,
          }}
        >
          <option value="All">All node types</option>
          <option value="Service">Services</option>
          <option value="Team">Teams</option>
          <option value="Incident">Incidents</option>
          <option value="Deployment">Deployments</option>
          <option value="Runbook">Runbooks</option>
        </select>

        <button
          className="secondary-button"
          type="button"
          onClick={zoomOut}
        >
          − Zoom out
        </button>

        <button
          className="secondary-button"
          type="button"
          onClick={zoomIn}
        >
          + Zoom in
        </button>

        <button
          className="primary-button"
          type="button"
          onClick={fitGraph}
        >
          Fit graph
        </button>
      </div>

      <div
        style={{
          display: "flex",
          gap: 12,
          flexWrap: "wrap",
          marginBottom: 12,
          fontSize: 12,
          color: "#cbd5e1",
        }}
      >
        {Object.entries(nodeColors).map(
          ([type, color]) => (
            <span
              key={type}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
              }}
            >
              <span
                style={{
                  width: 9,
                  height: 9,
                  borderRadius: "50%",
                  background: color,
                  display: "inline-block",
                }}
              />
              {type}
            </span>
          )
        )}

        <span>{nodes.length} nodes</span>
        <span>{edges.length} relationships</span>
      </div>

      <div
        ref={containerRef}
        role="application"
        aria-label="Interactive FalkorDB service topology graph"
        style={{
          width: "100%",
          height: 620,
          minWidth: 0,
          boxSizing: "border-box",
          background:
            "radial-gradient(circle at center, #1a2740 0%, #0d1422 78%)",
          border: "1px solid #263246",
          borderRadius: 12,
          overflow: "hidden",
        }}
      />

      {nodes.length === 0 && (
        <p style={{ color: "#fbbf24" }}>
          No graph nodes were received from the backend.
        </p>
      )}

      {selectedNode && (
        <section
          aria-label="Selected graph node details"
          style={{
            marginTop: 14,
            padding: 16,
            background: "#111827",
            border: "1px solid #334155",
            borderRadius: 12,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
              flexWrap: "wrap",
            }}
          >
            <h3 style={{ margin: 0, fontSize: 16 }}>
              {selectedNode.label}
            </h3>

            <button
              className="secondary-button"
              type="button"
              onClick={clearSelection}
            >
              Clear selection
            </button>
          </div>

          <p
            style={{
              color:
                nodeColors[selectedNode.type] ?? "#cbd5e1",
            }}
          >
            {selectedNode.type}
          </p>

          <dl
            style={{
              display: "grid",
              gridTemplateColumns:
                "minmax(100px, 150px) minmax(0, 1fr)",
              gap: "8px 14px",
              margin: 0,
              overflowWrap: "anywhere",
            }}
          >
            <dt>Node ID</dt>
            <dd style={{ margin: 0 }}>
              {selectedNode.id}
            </dd>

            {Object.entries(
              selectedNode.properties
            ).map(([key, value]) => (
              <div
                key={key}
                style={{ display: "contents" }}
              >
                <dt>{key.replaceAll("_", " ")}</dt>
                <dd style={{ margin: 0 }}>
                  {typeof value === "object" &&
                  value !== null
                    ? JSON.stringify(value)
                    : String(value ?? "—")}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}
    </div>
  );
}
