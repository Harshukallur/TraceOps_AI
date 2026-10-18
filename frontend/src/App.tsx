
import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import GraphView from "./GraphView";
import "./App.css";

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

type GraphData = {
  nodes: GraphNode[];
  edges: GraphEdge[];
};

type InvestigationEvidence = {
  service?: unknown;
  potentially_affected_services?: unknown;
  owners?: unknown;
  incidents?: unknown;
  runbooks?: unknown;
  deployments?: unknown;
};

type InvestigationResult = {
  evidence?: InvestigationEvidence;
  ai_analysis?: string;
  report?: string;
  error?: string;
  validation_warnings?: string[];
};

type Page = "investigator" | "topology" | "results";

const API_BASE = "http://127.0.0.1:5000";

const pageDetails: Record<
  Page,
  { eyebrow: string; title: string; description: string }
> = {
  investigator: {
    eyebrow: "OPERATIONS / AI INVESTIGATOR",
    title: "AI Investigator",
    description:
      "Investigate service failures using graph evidence and local AI.",
  },
  topology: {
    eyebrow: "OPERATIONS / CONNECTED DATA",
    title: "Service Topology",
    description:
      "Explore service dependencies, incidents, ownership, deployments, and runbooks.",
  },
  results: {
    eyebrow: "OPERATIONS / INVESTIGATION HISTORY",
    title: "Investigation Results",
    description:
      "Explore the graph evidence behind your latest AI investigation.",
  },
};

/**
 * Construct a focused evidence graph from FalkorDB's real graph data.
 *
 * Includes:
 * 1. The target service.
 * 2. Entities explicitly mentioned in the investigation evidence.
 * 3. Services that depend on the target, up to maxHops.
 * 4. Only relationships connecting the selected entities.
 *
 * The graph does not infer missing relationships or create nodes.
 */
function getInvestigationGraph(
  graph: GraphData,
  serviceName: string,
  maxHops = 2,
  evidence?: InvestigationEvidence,
): GraphData {
  const target = graph.nodes.find(
    (node) =>
      node.type.toLowerCase() === "service" &&
      node.label.trim().toLowerCase() ===
        serviceName.trim().toLowerCase(),
  );

  if (!target) {
    return { nodes: [], edges: [] };
  }

  const selected = new Set<string>([target.id]);
  const evidenceText = JSON.stringify(evidence ?? {}).toLowerCase();

  // Select only graph entities explicitly referenced by the evidence.
  for (const node of graph.nodes) {
    const label = node.label.trim().toLowerCase();
    const id = node.id.trim().toLowerCase();

    if (
      (label && evidenceText.includes(label)) ||
      (id && evidenceText.includes(id))
    ) {
      selected.add(node.id);
    }
  }

  // For A DEPENDS_ON B, failure of B may affect A.
  let frontier = new Set<string>([target.id]);
  const visitedServices = new Set<string>([target.id]);

  for (let hop = 0; hop < maxHops; hop++) {
    const next = new Set<string>();

    for (const edge of graph.edges) {
      if (edge.relationship.toUpperCase() !== "DEPENDS_ON") {
        continue;
      }

      if (
        frontier.has(edge.target) &&
        !visitedServices.has(edge.source)
      ) {
        const sourceNode = graph.nodes.find(
          (node) => node.id === edge.source,
        );

        if (sourceNode?.type.toLowerCase() === "service") {
          next.add(sourceNode.id);
        }
      }
    }

    for (const id of next) {
      visitedServices.add(id);
      selected.add(id);
    }

    frontier = next;

    if (frontier.size === 0) {
      break;
    }
  }

  // Keep actual relationships between selected nodes only.
  const relevantEdges = graph.edges.filter(
    (edge) =>
      selected.has(edge.source) &&
      selected.has(edge.target),
  );

  // Avoid showing isolated entities with no connecting relationship.
  const connectedIds = new Set<string>([target.id]);

  for (const edge of relevantEdges) {
    connectedIds.add(edge.source);
    connectedIds.add(edge.target);
  }

  return {
    nodes: graph.nodes.filter((node) => connectedIds.has(node.id)),
    edges: relevantEdges,
  };
}

/**
 * Normalize escaped Markdown and headings returned by local models.
 */
function normalizeModelMarkdown(text: string): string {
  return text
    .replace(/\\#/g, "#")
    .replace(/\\\*/g, "*")
    .replace(/\\_/g, "_")
    .replace(/\\`/g, "`")
    .replace(/([^\n])\s+(#{1,6}\s)/g, "$1\n\n$2")
    .replace(/\s+-\s+(?=\*\*)/g, "\n- ")
    .replace(/([^\n])\s+(-\s)/g, "$1\n$2")
    .trim();
}

async function readApiResponse<T>(response: Response): Promise<T> {
  const contentType = response.headers.get("content-type") ?? "";

  if (!contentType.includes("application/json")) {
    const body = await response.text();

    throw new Error(
      `The API returned a non-JSON response (HTTP ${response.status}). ${
        body.slice(0, 180) ||
        "Check that the correct Flask endpoint is running."
      }`,
    );
  }

  const data: unknown = await response.json();

  if (!response.ok) {
    const message =
      typeof data === "object" &&
      data !== null &&
      "error" in data &&
      typeof data.error === "string"
        ? data.error
        : `Request failed with HTTP ${response.status}.`;

    throw new Error(message);
  }

  return data as T;
}

function App() {
  const [page, setPage] = useState<Page>("investigator");
  const [selectedService, setSelectedService] =
    useState("Payment API");
  const [question, setQuestion] = useState("");

  const [graphData, setGraphData] = useState<GraphData>({
    nodes: [],
    edges: [],
  });

  const [backendStatus, setBackendStatus] =
    useState("Connecting...");
  const [graphError, setGraphError] = useState("");
  const [lastUpdated, setLastUpdated] = useState("");

  const [investigating, setInvestigating] = useState(false);
  const [investigationError, setInvestigationError] = useState("");

  const [investigationResult, setInvestigationResult] =
    useState<InvestigationResult | null>(null);

  const [reportService, setReportService] = useState("Payment API");

  useEffect(() => {
    let active = true;

    async function loadGraph() {
      try {
        const response = await fetch(`${API_BASE}/api/graph`);
        const data = await readApiResponse<GraphData>(response);

        if (
          !Array.isArray(data.nodes) ||
          !Array.isArray(data.edges)
        ) {
          throw new Error(
            "The graph API returned an unexpected response.",
          );
        }

        if (active) {
          setGraphData(data);
          setBackendStatus("Connected");
          setGraphError("");
          setLastUpdated(new Date().toLocaleTimeString());
        }
      } catch (error) {
        if (active) {
          setBackendStatus("Disconnected");
          setGraphError(
            error instanceof Error
              ? error.message
              : "Could not load graph data.",
          );
        }
      }
    }

    void loadGraph();

    return () => {
      active = false;
    };
  }, []);

  const services = graphData.nodes.filter(
    (node) => node.type.toLowerCase() === "service",
  );

  const activeIncidents = graphData.nodes.filter(
    (node) =>
      node.type.toLowerCase() === "incident" &&
      String(node.properties.status ?? "").toLowerCase() !==
        "resolved",
  ).length;

  const degradedServices = services.filter(
    (node) =>
      String(node.properties.status ?? "").toLowerCase() ===
      "degraded",
  ).length;

  // Results use a focused graph; topology uses the complete graph.
  const investigationGraph = useMemo(
    () =>
      getInvestigationGraph(
        graphData,
        reportService,
        2,
        investigationResult?.evidence,
      ),
    [graphData, reportService, investigationResult],
  );

  async function handleInvestigation() {
    if (investigating) {
      return;
    }

    if (!selectedService.trim()) {
      setInvestigationError(
        "Please select a service to investigate.",
      );
      return;
    }

    setInvestigating(true);
    setInvestigationError("");
    setInvestigationResult(null);

    try {
      const response = await fetch(
        `${API_BASE}/api/investigate`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            service_name: selectedService,
            question: question.trim(),
          }),
        },
      );

      const data =
        await readApiResponse<InvestigationResult>(response);

      // The backend may return either ai_analysis or report.
      const analysis = data.ai_analysis ?? data.report;

      if (!analysis && !data.evidence) {
        throw new Error(
          "The backend returned no report or evidence. Check the investigation endpoint.",
        );
      }

      // Normalize the report field for the existing UI renderer.
      // The spread preserves validation_warnings and other backend fields.
      setReportService(selectedService);
      setInvestigationResult({
        ...data,
        ai_analysis: analysis,
        validation_warnings: Array.isArray(data.validation_warnings)
          ? data.validation_warnings.filter(
              (warning): warning is string =>
                typeof warning === "string",
            )
          : [],
      });

      setPage("results");
    } catch (error) {
      setInvestigationError(
        error instanceof Error
          ? error.message
          : "Unable to run the investigation.",
      );
    } finally {
      setInvestigating(false);
    }
  }

  function renderReport() {
    if (!investigationResult) {
      return (
        <div className="panel empty-state">
          <div className="welcome-symbol">✳</div>
          <h3>No investigation results yet</h3>
          <p>
            Run an investigation from the AI Investigator page.
            Your AI analysis and focused graph evidence will appear
            here.
          </p>
          <button
            className="primary-button"
            type="button"
            onClick={() => setPage("investigator")}
          >
            Open AI Investigator
          </button>
        </div>
      );
    }

    const warnings = investigationResult.validation_warnings ?? [];

    return (
      <article className="panel report-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">INVESTIGATION REPORT</p>
            <h3>{reportService}</h3>
          </div>
          <span className="tag">ANALYSIS COMPLETE</span>
        </div>

        {investigationResult.ai_analysis && (
          <section className="report-section">
            <h4>AI analysis</h4>
            <div className="report-text">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {normalizeModelMarkdown(
                  investigationResult.ai_analysis,
                )}
              </ReactMarkdown>
            </div>
          </section>
        )}

        {warnings.length > 0 && (
          <section
            className="report-section validation-warning"
            aria-labelledby="validation-warnings-title"
            role="alert"
          >
            <h4 id="validation-warnings-title">
              Validation warnings ({warnings.length})
            </h4>

            <p className="panel-note">
              The report contains claims that may contradict
              retrieved evidence or need verification. Review these
              warnings before relying on the affected statements.
            </p>

            <ul>
              {warnings.map((warning, index) => (
                <li key={`${index}-${warning}`}>{warning}</li>
              ))}
            </ul>
          </section>
        )}

        <section className="report-section">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">
                FALKORDB · LIVE GRAPH DATA
              </p>
              <h4>Investigation evidence graph</h4>
            </div>

            <span className="tag">
              {investigationGraph.nodes.length} NODES
            </span>
          </div>

          <p className="panel-note">
            This focused graph shows the target service,
            evidence-linked entities, and dependent services within
            two hops. Unrelated graph entities are excluded. Click
            a node to inspect its properties and explore its
            immediate connections.
          </p>

          {backendStatus !== "Connected" ? (
            <div className="empty-state">
              <h3>Graph data unavailable</h3>
              <p>
                {graphError ||
                  "Waiting for the FalkorDB graph API."}
              </p>
            </div>
          ) : investigationGraph.nodes.length === 0 ? (
            <div className="empty-state">
              <h3>No connected evidence found</h3>
              <p>
                No matching service was found in the graph. Check
                the selected service name and graph data.
              </p>
            </div>
          ) : (
            <>
              <GraphView
                nodes={investigationGraph.nodes}
                edges={investigationGraph.edges}
              />

              <p className="panel-note">
                {investigationGraph.nodes.length} relevant nodes ·{" "}
                {investigationGraph.edges.length} relationships ·
                Graph data last refreshed{" "}
                {lastUpdated || "recently"}.
              </p>
            </>
          )}
        </section>

        <div className="report-actions">
          <button
            className="secondary-button"
            type="button"
            onClick={() => setPage("investigator")}
          >
            New investigation
          </button>

          <button
            className="secondary-button"
            type="button"
            onClick={() => setPage("topology")}
          >
            View full service topology
          </button>
        </div>
      </article>
    );
  }

  const currentPage = pageDetails[page];

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">T</div>

          <div>
            <h2>
              TraceOps <span>AI</span>
            </h2>
            <p>INCIDENT INTELLIGENCE</p>
          </div>
        </div>

        <p className="nav-label">WORKSPACE</p>

        <button
          className={`nav-item ${
            page === "investigator" ? "active" : ""
          }`}
          type="button"
          onClick={() => setPage("investigator")}
        >
          <span>✳</span> AI Investigator
        </button>

        <button
          className={`nav-item ${
            page === "topology" ? "active" : ""
          }`}
          type="button"
          onClick={() => setPage("topology")}
        >
          <span>⌘</span> Service topology
        </button>

        <button
          className={`nav-item ${
            page === "results" ? "active" : ""
          }`}
          type="button"
          onClick={() => setPage("results")}
        >
          <span>◷</span> Investigation results
        </button>

        <div className="sidebar-bottom">
          <div
            className="connection-dot"
            style={{
              background:
                backendStatus === "Connected"
                  ? "#45d6a1"
                  : backendStatus === "Disconnected"
                    ? "#ff7185"
                    : "#f5bb59",
            }}
          />

          <div>
            <strong>Graph database</strong>
            <p>
              {backendStatus === "Connected"
                ? "FalkorDB connected"
                : backendStatus === "Disconnected"
                  ? "Backend unavailable"
                  : "Connecting to Flask API..."}
            </p>
          </div>
        </div>
      </aside>

      <section className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">{currentPage.eyebrow}</p>
            <h1>{currentPage.title}</h1>
            <p className="page-description">
              {currentPage.description}
            </p>
          </div>

          <div className="model-badge">
            <span />
            LOCAL AI · QWEN
          </div>
        </header>

        {page === "investigator" && (
          <>
            <section className="welcome">
              <div>
                <p className="eyebrow">
                  GRAPH-POWERED INTELLIGENCE
                </p>

                <h2>
                  Understand the impact.
                  <br />
                  Resolve with confidence.
                </h2>

                <p>
                  Investigate service failures, discover dependency
                  impact, identify responsible teams, and get
                  evidence-based recommendations from your local AI.
                </p>
              </div>

              <div className="welcome-symbol">✳</div>
            </section>

            <section className="metrics">
              <article className="metric-card">
                <p>GRAPH NODES</p>
                <h3>
                  {backendStatus === "Connected"
                    ? graphData.nodes.length
                    : "—"}
                </h3>
                <span>Live entities from FalkorDB</span>
              </article>

              <article className="metric-card">
                <p>RELATIONSHIPS</p>
                <h3>
                  {backendStatus === "Connected"
                    ? graphData.edges.length
                    : "—"}
                </h3>
                <span>Live graph connections</span>
              </article>

              <article className="metric-card">
                <p>ACTIVE INCIDENTS</p>
                <h3>
                  {backendStatus === "Connected"
                    ? activeIncidents
                    : "—"}
                </h3>

                <span>
                  {backendStatus === "Connected"
                    ? `${degradedServices} degraded service${
                        degradedServices === 1 ? "" : "s"
                      }`
                    : "Waiting for graph data"}
                </span>
              </article>

              <article className="metric-card">
                <p>AI ENGINE</p>
                <h3 className="engine">Qwen 2.5</h3>
                <span>Local inference via Ollama</span>
              </article>
            </section>

            <section className="panel investigation-panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">AI INVESTIGATOR</p>
                  <h3>Investigate a service</h3>
                </div>

                <span className="ai-icon">✳</span>
              </div>

              {graphError && (
                <p role="alert" className="error-message">
                  {graphError}
                </p>
              )}

              <label htmlFor="service">Target service</label>

              <select
                id="service"
                value={selectedService}
                onChange={(event) =>
                  setSelectedService(event.target.value)
                }
                disabled={
                  backendStatus !== "Connected" ||
                  services.length === 0
                }
              >
                {services.length === 0 && (
                  <option value="Payment API">Payment API</option>
                )}

                {services.map((service) => (
                  <option key={service.id} value={service.label}>
                    {service.label}
                  </option>
                ))}
              </select>

              <label htmlFor="question">
                What do you want to investigate?
              </label>

              <textarea
                id="question"
                value={question}
                onChange={(event) =>
                  setQuestion(event.target.value)
                }
                placeholder="e.g. Why could payment failures affect checkout, and which team should investigate?"
              />

              <button
                className="primary-button"
                type="button"
                onClick={handleInvestigation}
                disabled={
                  backendStatus !== "Connected" ||
                  investigating ||
                  services.length === 0
                }
              >
                {investigating
                  ? "Analyzing graph evidence..."
                  : "✳ Run investigation"}
              </button>

              <p className="panel-note">
                {backendStatus !== "Connected"
                  ? "Waiting for a successful connection to Flask."
                  : investigating
                    ? "Retrieving graph evidence and generating local AI analysis."
                    : "Uses FalkorDB evidence and the local Qwen model."}
              </p>

              {investigationError && (
                <div role="alert" className="error-message">
                  <strong>Investigation failed</strong>
                  <p>{investigationError}</p>
                  <p>
                    Check that Flask implements POST
                    /api/investigate.
                  </p>
                </div>
              )}
            </section>
          </>
        )}

        {page === "topology" && (
          <section className="panel graph-page-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">CONNECTED DATA</p>
                <h3>Interactive service graph</h3>
              </div>

              <span className="tag">
                {backendStatus === "Connected"
                  ? "LIVE GRAPH DATA"
                  : "CONNECTING"}
              </span>
            </div>

            {graphError && (
              <p role="alert" className="error-message">
                {graphError}
              </p>
            )}

            {backendStatus !== "Connected" ? (
              <div className="empty-state">
                <h3>Waiting for FalkorDB data…</h3>
                <p>
                  Ensure Flask is running at 127.0.0.1:5000.
                </p>
              </div>
            ) : graphData.nodes.length === 0 ? (
              <div className="empty-state">
                <h3>No graph nodes found</h3>
                <p>The graph API returned no nodes.</p>
              </div>
            ) : (
              <>
                <GraphView
                  nodes={graphData.nodes}
                  edges={graphData.edges}
                />

                <div className="graph-legend">
                  {[
                    ["#7767f5", "Services"],
                    ["#20bfa5", "Teams"],
                    ["#f06478", "Incidents"],
                    ["#e5a64b", "Deployments"],
                    ["#4799e8", "Runbooks"],
                  ].map(([color, label]) => (
                    <span key={label}>
                      <i style={{ background: color }} />
                      {label}
                    </span>
                  ))}
                </div>

                <p className="panel-note">
                  {graphData.nodes.length} nodes ·{" "}
                  {graphData.edges.length} relationships · Updated{" "}
                  {lastUpdated || "recently"}. Drag nodes to explore
                  and zoom to inspect connections.
                </p>

                <div className="topology-actions">
                  <label htmlFor="topology-service">
                    Investigate a service
                  </label>

                  <select
                    id="topology-service"
                    value={selectedService}
                    onChange={(event) =>
                      setSelectedService(event.target.value)
                    }
                  >
                    {services.map((service) => (
                      <option
                        key={service.id}
                        value={service.label}
                      >
                        {service.label}
                      </option>
                    ))}
                  </select>

                  <button
                    className="primary-button"
                    type="button"
                    onClick={() => setPage("investigator")}
                  >
                    Open AI Investigator
                  </button>
                </div>
              </>
            )}
          </section>
        )}

        {page === "results" && renderReport()}

        <footer>
          TRACEOPS AI <span>·</span> GRAPH-POWERED INCIDENT RESPONSE
        </footer>
      </section>
    </main>
  );
}

export default App;
