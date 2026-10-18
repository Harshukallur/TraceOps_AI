# TraceOps AI

**Graph-powered incident investigation using FalkorDB, MCP, and a locally running LLM.**

TraceOps AI is an AI-assisted operational troubleshooting application that investigates services by traversing their dependencies and retrieving connected incidents, deployments, owning teams, and runbooks.

It uses FalkorDB as the primary graph database, a Model Context Protocol (MCP) server to expose graph investigation capabilities as tools, and Ollama with Qwen 2.5 3B for local language-model inference. A Flask backend orchestrates the investigation, while a React and TypeScript frontend displays the report and interactive service graph.

The system is designed to make incident investigation more explainable: graph queries supply the evidence, MCP makes investigation capabilities available as tools, and the LLM interprets the retrieved evidence rather than inventing operational facts.

---

## 1. Hackathon Track

### Track 1 — Agents That Act on Connected Data

TraceOps AI is submitted under **Track 1: Agents That Act on Connected Data**.

The project demonstrates how an AI-assisted agent can use connected operational data to investigate a service issue. Instead of treating services, incidents, teams, deployments, and runbooks as isolated records, it uses their relationships in FalkorDB to retrieve relevant evidence and identify potential impact.

For example, investigating `Payment API` can reveal:

- Checkout depends on Payment API.
- Order Management depends on Checkout, which depends on Payment API.
- Payment Platform owns Payment API.
- Incident INC-1045 is associated with Payment API.
- Runbook RB-PAY-01 is associated with Payment API.
- Deployment DEP-208 has a recorded relationship with an incident.

The system uses graph traversal and relationship queries to connect these facts. The local LLM then helps explain the evidence and its limitations.

The prototype focuses on investigation and evidence retrieval. It does not claim to perform autonomous production remediation.

---


## Architecture

TraceOps AI combines a local AI agent, MCP tools, and FalkorDB to investigate service dependencies, incidents, deployments, and troubleshooting runbooks.

![TraceOps AI Architecture](docs/traceops-architecture.png)


## 2. Problem Statement

When a production service encounters an issue, engineers need to determine which services depend on it, which incidents may be relevant, who owns the service, which troubleshooting procedures apply, and whether recent deployments deserve investigation.

These facts are often spread across different systems. Investigating them manually can be time-consuming, and an LLM operating without structured evidence may produce unsupported conclusions.

TraceOps AI addresses this problem by representing operational information as a graph and querying the graph during investigations.

The application combines:

1. Graph-based retrieval from FalkorDB.
2. MCP tools that expose investigation capabilities.
3. Local LLM inference for evidence interpretation.
4. Automated checks for dependency direction and unsupported causal claims.
5. An interactive frontend for inspecting results.

The result is an evidence-oriented investigation workflow that distinguishes potential impact and recorded correlations from confirmed outages or proven root causes.

---

## 3. Features

- **Graph-powered investigation:** Retrieve connected operational facts from FalkorDB.
- **Dependency impact analysis:** Discover dependent services and multi-hop dependency paths.
- **Hop-count calculation:** Report the number of dependency edges in each path.
- **Incident retrieval:** Identify associated incidents and their recorded severity and status.
- **Ownership discovery:** Find the team responsible for a service.
- **Runbook retrieval:** Identify relevant troubleshooting guidance.
- **Deployment correlation:** Inspect recorded relationships between deployments and incidents.
- **MCP tool integration:** Expose graph investigation operations as callable tools.
- **Local LLM interpretation:** Use Ollama with Qwen 2.5 3B.
- **Interactive service topology:** Explore nodes, relationships, and connected services.
- **Evidence-grounded reports:** Present investigation findings and limitations.
- **Validation tests:** Check dependency direction, causal-claim handling, service lookup, and deployment correlation.

---

## 4. Technology Stack

| Component | Technology | Responsibility |

| Graph database | FalkorDB | Stores operational entities and relationships |
| Graph query language | Cypher | Traverses dependencies and retrieves connected evidence |
| Agent-tool interface | Model Context Protocol (MCP) | Exposes graph investigation operations as tools |
| LLM runtime | Ollama | Runs inference locally |
| Language model | Qwen 2.5 3B | Interprets retrieved evidence |
| Backend | Python and Flask | Serves API requests and coordinates investigations |
| Frontend | React, TypeScript, Vite | Provides the investigation interface |
| Graph visualization | Cytoscape.js | Displays and explores graph topology |
| Configuration | python-dotenv | Loads environment configuration |
| Testing | pytest and unittest-compatible tests | Validates investigation behavior |

---

## 5. Architecture

```text
                     User
                      |
                      v
          React + TypeScript Frontend
                      |
                      v
                Flask Backend
                      |
                      v
          Investigation Orchestration
                      |
             +--------+--------+
             |                 |
             v                 v
       MCP Tool Calls     Local Ollama
             |             Qwen 2.5 3B
             v                 |
       MCP Server              |
             |                 |
             v                 |
       FalkorDB Graph           |
             |                 |
             v                 |
    Cypher Queries and          |
    Relationship Traversal      |
             |                 |
             +--------+--------+
                      |
                      v
           Evidence-based Report
                      |
                      v
              Frontend Results
```

The diagram represents the logical workflow. MCP is the tool interface for graph operations, FalkorDB supplies the connected data, and Ollama provides local inference. The precise process and transport arrangement should match the current implementation.

### Investigation flow

1. The user enters a service name and investigation question.
2. The backend validates the service against FalkorDB.
3. The investigation logic invokes graph queries and available MCP tools.
4. FalkorDB returns relevant service dependencies, incidents, owners, runbooks, and deployment relationships.
5. The LLM receives the retrieved context to help formulate an explanation.
6. The application validates selected report claims and presents the findings.
7. The frontend displays the report and graph evidence.

### Why FalkorDB is central

FalkorDB is not just a visualization layer. It stores the entities and relationships used to answer investigation questions.

The application depends on graph operations to:

- Traverse multi-hop dependency paths.
- Determine which services may be affected by a dependency.
- Connect services to their owning teams.
- Retrieve related incidents and runbooks.
- Inspect recorded deployment–incident relationships.

Replacing FalkorDB with a simple list of disconnected records would remove the graph traversal and relationship queries that support these investigations.

---

## 6. Graph Data Model

The sample graph represents services and the operational information needed to investigate them.

### 6.1 Node labels

The sample graph contains five node labels.

| Label | Purpose | Important properties |
|---|---|---|
| `Service` | An application or operational service | `id`, `name`, `status` |
| `Team` | The team responsible for a service | `name` |
| `Incident` | A recorded operational incident | `id`, `title`, `severity`, `status` |
| `Runbook` | Troubleshooting documentation | `id`, `title`, `instructions` |
| `Deployment` | A recorded software deployment | `id`, `version`, `status`, `description` |

These are the properties used by the sample queries and investigation behavior. Additional properties may exist in the actual graph.

### 6.2 Relationship types

| Relationship | Direction | Meaning |
|---|---|---|
| `DEPENDS_ON` | Service → Service | The source service depends on the target service |
| `OWNED_BY` | Service → Team | The team responsible for a service |
| `AFFECTED` | Incident → Service | The incident is recorded as affecting the service |
| `HAS_RUNBOOK` | Service → Runbook | The service is associated with a runbook |
| `DEPLOYED_TO` | Deployment → Service | The deployment is associated with the service |
| `FOLLOWED_BY` | Deployment → Incident | The graph records that the incident followed the deployment |

**Relationship direction is important.** For `DEPENDS_ON`, an edge from Checkout to Payment API means Checkout depends on Payment API. It does not mean Payment API depends on Checkout.

Likewise, `FOLLOWED_BY` represents a recorded temporal association in this dataset. It does not prove that the deployment caused the incident.

### 6.3 Sample graph topology

```text
Order Management
       |
   DEPENDS_ON
       v
    Checkout
       |
   DEPENDS_ON
       v
   Payment API
       |
       +------ OWNED_BY ------> Payment Platform
       |
       +------ HAS_RUNBOOK ---> RB-PAY-01

INC-1045 ------ AFFECTED -----> Payment API

DEP-208 ------- DEPLOYED_TO --> Payment API
   |
 FOLLOWED_BY
   v
Incident
```

The diagram is a simplified illustration of the sample graph. The actual relationships should be verified against the running database.

### 6.4 Sample entities

The current sample dataset includes the following entities:

**Services**

- Payment API — degraded
- Checkout — healthy
- Order Management — healthy
- Auth Service — healthy
- Notification Service — healthy

**Teams**

- Payment Platform
- Commerce Engineering
- Identity Platform

**Incidents**

- INC-1045 — Payment errors after deployment; high severity; investigating
- INC-1032 — Authentication timeout; medium severity; resolved

**Deployment**

- DEP-208 — version 2.4.1; Payment API release

**Runbooks**

- RB-PAY-01
- RB-AUTH-01

These values are sample graph records, not a live production monitoring feed.

### 6.5 Expected graph counts

The populated sample graph was previously verified with:

| Entity or relationship | Count |
|---|---:|
| Service nodes | 5 |
| Team nodes | 3 |
| Incident nodes | 2 |
| Runbook nodes | 2 |
| Deployment nodes | 1 |
| **Total nodes** | **13** |
| Relationships | **14** |

These are the previously observed counts; the live health endpoint can be used to verify the current database state.

### 6.6 Graph schema summary

```text
(Service)-[:DEPENDS_ON]->(Service)
(Service)-[:OWNED_BY]->(Team)
(Incident)-[:AFFECTED]->(Service)
(Service)-[:HAS_RUNBOOK]->(Runbook)
(Deployment)-[:DEPLOYED_TO]->(Service)
(Deployment)-[:FOLLOWED_BY]->(Incident)
```

---

## 7. Cypher Queries and Graph Algorithms

The following queries document the graph operations on which the investigation workflow depends. Run them through the FalkorDB browser interface or the project's graph-query layer.

Open `http://127.0.0.1:3000` and select the `traceops` graph.

### 7.1 Inspect graph nodes and relationships

```cypher
MATCH (a)-[r]->(b)
RETURN a, r, b
LIMIT 100
```

**Purpose:** Inspect the graph topology and understand how operational entities are connected.

### 7.2 Find a service by name

```cypher
MATCH (s:Service {name: 'Payment API'})
RETURN s
```

**Purpose:** Retrieve the service node used to begin an investigation.

### 7.3 Find direct dependencies of a service

```cypher
MATCH (s:Service {name: 'Checkout'})-[:DEPENDS_ON]->(dependency:Service)
RETURN s.name AS service,
       dependency.name AS dependency
```

**Purpose:** Find the services Checkout directly depends on.

### 7.4 Find services that directly depend on Payment API

```cypher
MATCH (dependent:Service)-[:DEPENDS_ON]->(target:Service {name: 'Payment API'})
RETURN dependent.name AS dependent_service,
       target.name AS dependency
```

**Purpose:** Identify immediate dependents of Payment API.

Expected sample result:

| Dependent service | Dependency |
|---|---|
| Checkout | Payment API |

### 7.5 Discover multi-hop dependency paths

```cypher
MATCH p = (dependent:Service)-[:DEPENDS_ON*1..5]->(target:Service {name: 'Payment API'})
RETURN p
```

**Purpose:** Discover dependency paths of one to five edges leading to Payment API.

Expected sample paths:

```text
Checkout -> Payment API
Order Management -> Checkout -> Payment API
```

The path length represents the number of dependency relationships traversed.

### 7.6 Calculate hop counts

```cypher
MATCH p = (dependent:Service)-[:DEPENDS_ON*1..5]->(target:Service {name: 'Payment API'})
RETURN dependent.name AS dependent_service,
       [node IN nodes(p) | node.name] AS dependency_path,
       length(p) AS hops
ORDER BY hops ASC
```

**Purpose:** Return the path and number of edges in each discovered dependency chain.

Expected sample results:

| Dependent service | Path | Hops |
|---|---|---:|
| Checkout | Checkout → Payment API | 1 |
| Order Management | Order Management → Checkout → Payment API | 2 |

The investigation code should also guard against duplicate paths if the graph contains multiple routes to the same target.

### 7.7 Find the owning team

```cypher
MATCH (s:Service {name: 'Payment API'})-[:OWNED_BY]->(t:Team)
RETURN s.name AS service,
       t.name AS owning_team
```

**Purpose:** Identify the team associated with the service.

Expected sample owner: Payment Platform.

### 7.8 Retrieve incidents affecting a service

```cypher
MATCH (i:Incident)-[:AFFECTED]->(s:Service {name: 'Payment API'})
RETURN i.id AS incident_id,
       i.title AS title,
       i.severity AS severity,
       i.status AS status
```

**Purpose:** Retrieve incident context linked to Payment API.

Expected sample incident: INC-1045, with high severity and investigating status.

### 7.9 Retrieve runbooks for a service

```cypher
MATCH (s:Service {name: 'Payment API'})-[:HAS_RUNBOOK]->(r:Runbook)
RETURN r.id AS runbook_id,
       r.title AS title,
       r.instructions AS instructions
```

**Purpose:** Retrieve troubleshooting guidance associated with the service.

Expected sample runbook: RB-PAY-01.

### 7.10 Inspect deployment-to-service relationships

```cypher
MATCH (d:Deployment)-[:DEPLOYED_TO]->(s:Service)
RETURN d.id AS deployment_id,
       d.version AS version,
       s.name AS service
```

**Purpose:** Find which service a recorded deployment targets.

### 7.11 Inspect deployment–incident correlations

```cypher
MATCH (d:Deployment)-[:FOLLOWED_BY]->(i:Incident)
RETURN d.id AS deployment_id,
       i.id AS incident_id,
       i.title AS incident_title,
       i.severity AS severity,
       i.status AS status
```

**Purpose:** Retrieve incidents connected to deployments in the graph.

**Important:** A recorded `FOLLOWED_BY` relationship does not establish causation. A deployment may precede an incident without causing it.

### 7.12 Traverse the service graph from Auth Service

```cypher
MATCH p = (dependent:Service)-[:DEPENDS_ON*1..5]->(target:Service {name: 'Auth Service'})
RETURN [node IN nodes(p) | node.name] AS dependency_path,
       length(p) AS hops
ORDER BY hops ASC
```

**Purpose:** Identify services that depend directly or indirectly on Auth Service.

Expected sample paths include:

```text
Payment API -> Auth Service
Checkout -> Payment API -> Auth Service
Order Management -> Checkout -> Payment API -> Auth Service
```

### 7.13 Find all runbooks and incidents linked to a service

```cypher
MATCH (s:Service {name: 'Payment API'})
OPTIONAL MATCH (i:Incident)-[:AFFECTED]->(s)
OPTIONAL MATCH (s)-[:HAS_RUNBOOK]->(r:Runbook)
RETURN s.name AS service,
       collect(DISTINCT i.id) AS incidents,
       collect(DISTINCT r.id) AS runbooks
```

**Purpose:** Combine incident and runbook context for a service into one result. `OPTIONAL MATCH` allows the service to be returned even if one of these relationship types is absent.

### 7.14 Graph operations used by TraceOps AI

The core graph algorithms and operations are:

1. **Service lookup:** Match a requested service by its canonical name.
2. **Dependency traversal:** Follow directed `DEPENDS_ON` edges.
3. **Multi-hop path discovery:** Find indirect dependents through intermediate services.
4. **Hop-count calculation:** Measure the number of relationships in a discovered path.
5. **Relationship-based retrieval:** Retrieve owners, incidents, runbooks, and deployments.
6. **Correlation inspection:** Retrieve deployment–incident relationships while preserving the distinction between association and causation.

These operations provide structured evidence for the investigation report. They do not by themselves establish that a service is currently down or identify a definitive root cause.

---

## 8. MCP Integration

### 8.1 What MCP does in TraceOps AI

The Model Context Protocol (MCP) is the tool interface used to expose application capabilities to an AI workflow.

In TraceOps AI, graph investigation operations are represented as tools so that the investigation logic can request structured information about services and their connected operational context.

The intended division of responsibilities is:

- **FalkorDB:** Stores graph entities and relationships.
- **Cypher queries:** Retrieve and traverse the graph.
- **MCP server:** Exposes supported investigation operations as tools.
- **Investigation orchestration:** Coordinates tool use and report generation.
- **Ollama / Qwen 2.5 3B:** Interprets the retrieved context locally.
- **Validation logic:** Checks selected claims and detects known unsupported statements.
- **Frontend:** Presents the report and graph to the user.

MCP is not the graph database, and it does not replace Cypher. It provides a standardized way to expose graph operations as callable tools.

### 8.2 MCP tools

The current TraceOps AI MCP tool set includes the following operations.

| Tool | Purpose | Investigation value |
|---|---|---|
| `get_service_details` | Retrieve service details | Establishes the service and its recorded properties |
| `find_dependencies` | Discover service dependencies | Supports direct and multi-hop impact analysis |
| `get_service_owner` | Retrieve the owning team | Identifies the team responsible for the service |
| `get_related_incidents` | Retrieve related incidents | Supplies incident titles, severity, and status |
| `get_service_runbooks` | Retrieve linked runbooks | Provides relevant troubleshooting guidance |
| `get_incident_deployment_correlations` | Inspect deployment–incident links | Surfaces recorded correlations without assuming causation |

The tool names describe their intended responsibilities. Exact argument schemas, return fields, and transport configuration should be taken from the current MCP server implementation.

### 8.3 Example investigation using MCP tools

For a request such as:

> Investigate Payment API and identify potential impact, related incidents, owning team, and runbook guidance.

The investigation workflow can use the tools as follows:

1. `get_service_details` retrieves the service record.
2. `find_dependencies` retrieves dependent services and dependency paths.
3. `get_service_owner` retrieves the owning team.
4. `get_related_incidents` retrieves linked incident records.
5. `get_service_runbooks` retrieves the associated runbook.
6. `get_incident_deployment_correlations` retrieves recorded deployment–incident relationships when relevant.


for example:
Payment API
“Investigate Payment API and identify why it is degraded. Find related incidents, recent deployment correlations, service dependencies, owning team, and relevant runbooks.”
Expected evidence
- Incident INC-1045 — high severity, investigating.
- Deployment DEP-208 — version v2.4.1.
- Owner: Payment Platform.
- Related runbook: RB-PAY-01.

“Investigate Checkout. Which downstream services does it depend on, which upstream services may be impacted by a Checkout issue, and what incidents or runbooks are relevant?”
Expected evidence
- Checkout depends on Payment API.
- Checkout is owned by Commerce Engineering.
- Payment API is a related downstream dependency.
- Check connected incidents and runbooks.
    Copy prompt

### 8.4 Why MCP is useful

MCP provides a clean boundary between the reasoning workflow and the operations that retrieve data.

It makes the investigation capabilities easier to expose, test, and reuse. Instead of requiring the language model to construct arbitrary database operations, the application can offer defined tools with controlled responsibilities.

This also helps keep operational facts grounded in FalkorDB responses rather than relying exclusively on the LLM's generated text.

### 8.5 MCP and safety

The tools retrieve operational evidence. They should not be treated as proof of facts that the graph does not contain.

For example:

- A dependency path indicates potential impact, not a confirmed outage.
- An incident relationship indicates recorded association, not necessarily current service health.
- A deployment–incident correlation does not establish root cause.
- A runbook recommendation does not mean remediation was executed.

TraceOps AI currently focuses on investigation, not autonomous production remediation.

---

## 9. Local LLM

TraceOps AI uses Ollama with `qwen2.5:3b` for local language-model inference.

The model helps explain evidence retrieved through the graph investigation workflow. FalkorDB remains the source of the structured service relationships and recorded operational entities.

### Why local inference?

- Avoids sending investigation prompts to an external hosted LLM provider in the intended local setup.
- Supports experimentation on a developer machine.
- Keeps graph retrieval separate from natural-language interpretation.
- Allows investigation prompts and outputs to be tested locally.

Local execution still depends on the computer's available memory, CPU, GPU, and configuration. The application should not send graph credentials or unrelated secrets to the model.

---

## 10. Evidence Validation

TraceOps AI includes validation tests for selected classes of investigation claims.

### Dependency direction

The graph uses directed relationships. The system should preserve the correct meaning of a dependency and detect reversed claims.

### Causal claims

A deployment followed by an incident does not automatically prove that the deployment caused it. The validation logic tests whether explicit non-causation statements are incorrectly flagged and whether unsupported positive causal claims are detected.

### Evidence limitations

Reports should distinguish:

- Recorded graph facts.
- Potential impact inferred from dependency paths.
- Historical incident context.
- Deployment–incident correlations.
- Hypotheses that require additional evidence.

The current validation is a prototype-level safeguard, not a comprehensive guarantee that every LLM statement is correct.

---

## 11. Installation and Setup

### Prerequisites

- Windows 10 or 11
- Python 3.12
- Git
- Node.js and npm
- Docker Desktop
- Ollama

Verify the tools:

```powershell
python --version
git --version
docker --version
node --version
npm --version
ollama --version
```

### Step 1: Clone or open the repository

If the project has been published:

```powershell
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd traceops-ai
```

Replace the placeholder with the actual repository URL.

If you already have the project, navigate to its root directory instead.

### Step 2: Start FalkorDB

```powershell
docker compose up -d
docker compose ps
```

The local Compose configuration exposes FalkorDB on `127.0.0.1:6379` and its browser interface on `127.0.0.1:3000`.

### Step 3: Set up Python

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Step 4: Configure environment variables

Create `.env` only if needed by the current configuration code. For the local setup, the example configuration is:

```dotenv
FALKORDB_HOST=127.0.0.1
FALKORDB_PORT=6379
FALKORDB_GRAPH=traceops
```

Confirm the expected variable names in the project code before changing configuration. Do not commit `.env` or secrets.

### Step 5: Test the database connection

```powershell
.\.venv\Scripts\python.exe scripts\test_connection.py
```

### Step 6: Seed the sample graph if required

**Warning: the seed script deletes existing graph nodes and relationships before recreating the sample graph.**

Run it only if you intentionally want to reset the data:

```powershell
.\.venv\Scripts\python.exe scripts\seed_graph.py
```

Skip this step if the graph is already populated.

### Step 7: Install and start Ollama

Install Ollama from its official website: https://ollama.com/

Download the model:

```powershell
ollama pull qwen2.5:3b
ollama list
```

Test it if necessary:

```powershell
ollama run qwen2.5:3b
```

### Step 8: Install frontend dependencies

```powershell
cd frontend
npm install
```

---

## 12. Running the Application

Start FalkorDB and make sure Ollama is available.

### Terminal 1: Backend

From the project root:

```powershell
.\.venv\Scripts\python.exe -m app.server
```

The backend should be available at `http://127.0.0.1:5000`.

Health endpoint: `http://127.0.0.1:5000/api/health`

### Terminal 2: Frontend

```powershell
cd C:\Users\win10\Desktop\traceops-ai\frontend
npm run dev
```

Open the Vite URL printed in the terminal, normally `http://localhost:5173`.

---

## 13. API Reference

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check backend and graph connectivity |
| GET | `/api/graph` | Retrieve graph visualization data |
| POST | `/api/investigate` | Run a service investigation |

### Example investigation request in PowerShell

```powershell
$body = @{
    service_name = "Payment API"
    question = "Investigate this service and identify potential impact."
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://127.0.0.1:5000/api/investigate" `
    -Method Post `
    -ContentType "application/json" `
    -Body $body
```

The exact response schema depends on the current backend implementation.

---

## 14. Testing

Run the complete test suite from the project root:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -v
```

The previously verified result was **10 tests passed**.

The suite covers:

- Service investigation and input validation.
- Case-insensitive service lookup.
- Dependency direction and reversal detection.
- Causal-claim validation.
- Deployment–incident correlation.

Frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

The frontend lint and production build previously completed successfully. Re-run them after any code changes.

---

## 15. Troubleshooting

### FalkorDB connection failure

- Ensure Docker Desktop is running.
- Run `docker compose ps`.
- Verify the host, port, and graph name.
- Inspect logs with `docker compose logs`.

### Ollama unavailable

- Ensure Ollama is running.
- Run `ollama list`.
- Confirm `qwen2.5:3b` is installed.
- Test with `ollama run qwen2.5:3b`.

### Python dependencies missing

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Frontend dependencies missing

From `frontend`:

```powershell
npm install
npm run lint
npm run build
```

### Service not found

Check the service name and confirm the graph is populated. Do not reseed a graph containing data you want to preserve.

---

## 16. Limitations

- The current graph contains sample operational data rather than live production telemetry.
- Dependency paths indicate potential impact, not confirmed outages.
- Deployment–incident relationships do not establish root cause.
- The LLM can make mistakes; its explanations must be checked against graph evidence.
- Validation checks cover selected known failure modes rather than all possible hallucinations.
- The prototype does not execute production remediation.
- Local inference performance depends on available hardware.

## 17. Future Improvements

- Integrate live monitoring and incident-management systems.
- Add richer graph-based incident timelines.
- Expand automated tests for MCP tool contracts and report evaluation.
- Improve evidence traceability for individual report statements.
- Add authentication and role-based permissions for multi-user deployments.
- Introduce safe, approval-based remediation workflows.

---

## 18. Graph Hacks Summary

**Track:** Track 1 — Agents That Act on Connected Data

TraceOps AI combines FalkorDB graph traversal, MCP-based investigation tools, and local LLM interpretation to help engineers investigate interconnected operational services.

FalkorDB is central to the application because the investigation depends on querying the graph's entities and relationships. MCP exposes the investigation capabilities, while the local model helps explain the evidence returned by those operations.

The project aims to make AI-assisted troubleshooting more transparent by presenting dependency paths, related incidents, ownership, runbooks, and evidence limitations in a single workflow.
![alt text](<TraceOps AI Investigation Architecture.png>)