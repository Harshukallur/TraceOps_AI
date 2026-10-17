# TraceOps AI

**Graph-powered incident investigation for AI agents, built with FalkorDB and a local LLM.**

TraceOps AI helps engineers investigate service dependencies, discover related incidents, identify owning teams, find relevant runbooks, and understand potential impact through an interactive dependency graph and an AI-generated investigation report.

The project uses **FalkorDB as its central graph database** and **Ollama to run the Qwen 2.5 3B language model locally**. The application retrieves operational evidence from the graph and uses the local model to explain that evidence.

## Table of Contents

- [Problem Statement](#problem-statement)
- [Features](#features)
- [Architecture](#architecture)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation and Setup](#installation-and-setup)
- [Running TraceOps AI](#running-traceops-ai)
- [Testing the Application](#testing-the-application)
- [Example Cypher Queries](#example-cypher-queries)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Limitations](#limitations)

## Problem Statement

Modern systems contain interconnected services, teams, incidents, deployments, and troubleshooting procedures. When a service encounters a problem, engineers need to understand which other services may be affected and where to investigate.

Searching through disconnected records can make this process slow and difficult.

TraceOps AI represents these operational relationships as a graph. Engineers can investigate a service, traverse its dependencies, retrieve relevant incidents and runbooks, and view an evidence-based report in one interface.

## Features

- **Graph-powered investigations:** Retrieve service relationships and operational records from FalkorDB.
- **Dependency impact analysis:** Explore dependency paths and the number of hops between services.
- **Incident context:** Identify related incidents, including their severity and status.
- **Ownership discovery:** Find the team responsible for a service.
- **Runbook recommendations:** Retrieve relevant troubleshooting instructions from the graph.
- **Local AI interpretation:** Use Ollama with Qwen 2.5 3B to explain the retrieved evidence.
- **Interactive dependency graph:** Explore nodes and relationships, search for services, filter node types, zoom, and inspect node properties.
- **Evidence-grounded reporting:** Present findings, potential impact, investigation steps, and limitations.
- **Local inference:** Run the language model on your own machine without sending prompts to an external LLM API provider.

## Architecture

```text
User
 |
 v
React + TypeScript Frontend
 |                 |
 | Graph data      | Investigation request
 v                 v
Interactive      Flask Backend
Graph View           |
                     v
               Investigation Logic
                     |
                     v
                FalkorDB Graph
                     |
                     v
            Services, Dependencies,
            Incidents, Teams, Runbooks
                     |
                     v
               Local Ollama
               Qwen 2.5 3B
                     |
                     v
           Investigation Report
                     |
                     v
             Frontend Results
```

### How it works

1. The user selects or enters a service, such as `Payment API`.
2. The Flask backend validates the service against FalkorDB.
3. Graph queries retrieve dependency paths, related incidents, owning teams, and runbooks.
4. The local language model interprets the retrieved evidence.
5. The application combines the graph-derived facts with the AI interpretation to produce an investigation report.
6. The frontend displays the report and the interactive graph.

**Why FalkorDB matters:** The graph is not just a visualization. It stores and connects operational entities, and its relationships are queried to retrieve the evidence used in an investigation.

## Technology Stack

| Component | Technology | Purpose |

| Frontend | React, TypeScript, Vite | Interactive web application |
| Graph visualization | Cytoscape.js | Display and explore graph relationships |
| Backend | Python, Flask, Flask-CORS | API and investigation workflow |
| Graph database | FalkorDB | Store and query operational relationships |
| Local LLM runtime | Ollama | Run inference locally |
| Language model | Qwen 2.5 3B | Interpret graph evidence |
| HTTP client | Python Requests | Communicate with Ollama |
| Configuration | python-dotenv | Load environment configuration |
| Testing | pytest | Support automated tests |

## Prerequisites

Install the following before starting:

- Windows 10 or 11
- Python 3.12
- Git
- Node.js and npm
- Docker Desktop with its Linux container engine running
- Ollama
- Sufficient memory and disk space for the local model

Check the installations in PowerShell:

```powershell
python --version
git --version
docker --version
node --version
npm --version
ollama --version
```

If `python` does not select Python 3.12, use the Python launcher:

```powershell
py -3.12 --version
```

## Installation and Setup

### 1. Clone the repository

Replace the placeholder URL with the actual public GitHub repository URL after publishing the project.

```powershell
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd traceops-ai
```

If you already have the project locally, navigate to its root directory instead.

### 2. Start FalkorDB

From the project root, run:

```powershell
docker compose up -d
```

Check the container:

```powershell
docker compose ps
```

The provided Compose configuration exposes:

- FalkorDB: `127.0.0.1:6379`
- FalkorDB browser interface: `http://127.0.0.1:3000`

Keep the database running while using the application.

### 3. Create the Python environment

From the project root:

```powershell
py -3.12 -m venv .venv
```

Install the Python dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root, using the following local defaults if they match your configuration:

```dotenv
FALKORDB_HOST=127.0.0.1
FALKORDB_PORT=6379
FALKORDB_GRAPH=traceops
```

Do not commit passwords, API keys, or other secrets to Git.

### 5. Verify the FalkorDB connection

Run:

```powershell
.\.venv\Scripts\python.exe scripts\test_connection.py
```

Expected output should indicate that TraceOps AI connected successfully to FalkorDB.

If the connection fails, verify that Docker is running and that the database container is healthy.

### 6. Populate the sample graph

If the database is empty, run the project's graph-seeding script:

```powershell
.\.venv\Scripts\python.exe scripts\seed_graph.py
```

**Warning:** The current seed script begins by deleting existing graph nodes and relationships. Run it only when you intend to reset and repopulate the graph. Do not run it against data you need to preserve.

The sample graph includes services, teams, incidents, a deployment, and runbooks.

### 7. Install and start Ollama

Install Ollama from its official website:

https://ollama.com/

Download the model used by TraceOps AI:

```powershell
ollama pull qwen2.5:3b
```

Confirm that the model is available:

```powershell
ollama list
```

Check that the local Ollama service is running. On a typical local installation, its API is available at:

`http://localhost:11434`

You can test the model directly:

```powershell
ollama run qwen2.5:3b
```

Enter a simple prompt such as:

```text
Explain why dependency relationships are useful during incident investigation.
```

Exit the interactive session when finished.

TraceOps AI uses the Ollama chat API and the `qwen2.5:3b` model. Model inference runs locally, although performance depends on the computer's available CPU, memory, and GPU resources.

### 8. Install frontend dependencies

Open a new terminal:

```powershell
cd frontend
npm install
```

## Running TraceOps AI

Keep the database and Ollama available while running the application.

### Terminal 1: Start the backend

From the project root:

```powershell
.\.venv\Scripts\python.exe -m app.server
```

The Flask backend should be available at:

`http://127.0.0.1:5000`

Check the health endpoint:

```text
http://127.0.0.1:5000/api/health
```

### Terminal 2: Start the frontend

```powershell
cd frontend
npm run dev
```

Open the Vite URL printed in the terminal, normally:

`http://localhost:5173`

You should now be able to explore the graph and run an investigation.




## Testing the Application

### Test 1: Investigate Payment API

In the AI Investigator interface, enter:

```text- Input
Payment API
```
##Command to run investigator- Investigate this service and identify potential impact, related incidents, owning team, and recommended runbook steps. Include the exact dependency paths and hop counts. Clearly distinguish potential impact from a confirmed outage, and do not assume a root cause.

Expected evidence includes:

What it should demonstrate
- Checkout: Checkout → Payment API — 1 hop.
- Order Management: Order Management → Checkout → Payment API — 2 hops.
- Owning team: Payment Platform.
- Related incident: INC-1045.
- Runbook: RB-PAY-01.

The graph should show the relevant service and its connected evidence. Dependency relationships indicate potential impact; they do not prove that another service is experiencing an outage.

### Test 2: Investigate Auth Service

Enter:

```text-Input
Auth Service
```

##Command-Investigate Auth Service and explain which dependent services could be affected if it experiences a problem. Include each exact dependency path and hop count, related incidents and their current recorded status, the owning team, and the recommended runbook steps. Do not treat a historical resolved incident as proof of current service health.

Expected evidence includes:

What it should demonstrate
- Payment API: Payment API → Auth Service — 1 hop.
- Checkout: Checkout → Payment API → Auth Service — 2 hops.
- Order Management: Order Management → Checkout → Payment API → Auth Service — 3 hops.
- Owning team: Identity Platform.
- Related incident: INC-1032 (medium, resolved).
- Runbook: RB-AUTH-01

A resolved historical incident does not establish the current health of a service.

### Test 3: Search for an unknown service

Enter:

```text
Unknown Service
```

Expected behavior: the backend should report that the service was not found rather than inventing graph evidence.

### Test 4: Explore the graph

In the interactive graph:

1. Search for `Payment API`.
2. Select a node to inspect its properties.
3. Explore its connected nodes and relationships.
4. Try the node-type filter.
5. Use zoom and fit controls to navigate the graph.

### Test 5: Check the API directly

The graph endpoint can be opened in a browser:

```text
http://127.0.0.1:5000/api/graph
```

It should return graph visualization data containing `nodes` and `edges`.

## Example Cypher Queries

You can run Cypher queries through the FalkorDB browser interface at `http://127.0.0.1:3000`, selecting the `traceops` graph.

The examples below use the sample graph's entity labels and relationship types. If you change the schema, adjust the queries accordingly.

### 1. View all nodes and relationships

```cypher
MATCH (a)-[r]->(b)
RETURN a, r, b
LIMIT 100
```

### 2. Find Payment API

```cypher
MATCH (s:Service {name: 'Payment API'})
RETURN s
```

### 3. Find services that depend on Payment API

```cypher
MATCH (s:Service)-[:DEPENDS_ON]->(target:Service {name: 'Payment API'})
RETURN s.name AS dependent_service, target.name AS dependency
```

### 4. Find the team responsible for Payment API

```cypher
MATCH (s:Service {name: 'Payment API'})-[:OWNED_BY]->(t:Team)
RETURN s.name AS service, t.name AS owning_team
```

### 5. Find incidents affecting Payment API

```cypher
MATCH (i:Incident)-[:AFFECTED]->(s:Service {name: 'Payment API'})
RETURN i.id AS incident_id,
       i.title AS title,
       i.severity AS severity,
       i.status AS status
```

### 6. Find Payment API's runbooks

```cypher
MATCH (s:Service {name: 'Payment API'})-[:HAS_RUNBOOK]->(r:Runbook)
RETURN r.id AS runbook_id,
       r.title AS title,
       r.instructions AS instructions
```

### 7. Explore multi-hop dependency paths

```cypher
MATCH p = (dependent:Service)-[:DEPENDS_ON*1..5]->(target:Service {name: 'Payment API'})
RETURN p
```

This explores dependency paths of one to five relationships leading to Payment API. The direction of the relationship matters.

### 8. Find deployments followed by incidents

```cypher
MATCH (d:Deployment)-[:FOLLOWED_BY]->(i:Incident)
RETURN d.id AS deployment_id,
       i.id AS incident_id,
       i.title AS incident_title
```

This query finds recorded graph relationships. It does not prove that a deployment caused an incident.

## API Reference

The Flask application currently exposes the following routes:

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Check backend and graph connectivity |
| GET | `/api/graph` | Retrieve graph nodes and edges |
| POST | `/api/investigate` | Run a service investigation |

### Example investigation request

The investigation endpoint accepts a JSON body with a service name and a question. For example:

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

The response contains investigation information and the generated report. The exact response fields depend on the current backend implementation.

## Troubleshooting

### FalkorDB connection fails

- Check Docker Desktop.
- Run `docker compose ps`.
- Confirm the configured host, port, and graph name.
- Inspect container logs using `docker compose logs`.

### Ollama is unavailable

- Confirm Ollama is installed and running.
- Run `ollama list`.
- Confirm `qwen2.5:3b` is available.
- Test the model with `ollama run qwen2.5:3b`.
- Check whether another process is using the configured local API port.

### Python dependency errors

Run the installation command again:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Frontend dependency errors

From the `frontend` directory:

```powershell
npm install
npm run build
```

### A service is not found

Verify that the graph has been populated and that the service name matches a node in FalkorDB.

## Limitations

- The project currently uses a sample operational graph, not a live production monitoring system.
- Potential impact is inferred from recorded dependency paths; it is not confirmation of a real outage.
- The language model interprets supplied evidence and should not be treated as the source of operational facts.
- Root cause is not established unless the available evidence explicitly supports it.
- The local model's response time depends on available hardware.
- The current prototype does not execute remediation actions against production services.

## Future Improvements

- Connect live monitoring and incident-management data sources.
- Add graph-based incident timelines and deployment correlation.
- Expand automated tests for investigation and dependency queries.
- Improve report evaluation and evidence traceability.
- Add authenticated access and role-based permissions for multi-user deployments.

## Graph Hacks

TraceOps AI is built for the Graph Hacks challenge, with FalkorDB as the primary graph database and a local LLM for evidence interpretation.

The project demonstrates how connected operational data can help an AI assistant investigate service dependencies, retrieve related context, and produce explainable findings.

