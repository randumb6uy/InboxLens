# Graph Report - IndexLens  (2026-09-24)

## Corpus Check
- Corpus is ~2,534 words - fits in a single context window. You may not need a graph.

## Summary
- 36 nodes · 26 edges · 13 communities (5 shown, 8 thin omitted)
- Extraction: 96% EXTRACTED · 4% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.95)
- Token cost: 2,534 input · 1,200 output

## Community Hubs (Navigation)
- Multi-Agent System & Agents
- Ingestion, Routing & Gateway
- Next.js Multi-Tab Dashboard
- Pydantic Extraction Schemas
- Storage, Embeddings & Query Layer
- Graphify Agent Customizations
- Architecture Specification
- Roadmap: Foundations
- Roadmap: Classification & Storage
- Roadmap: LLM Extraction
- Roadmap: React Dashboard
- Roadmap: Semantic Search & RAG
- Roadmap: Multi-Agent Layer

## God Nodes (most connected - your core abstractions)
1. `Multi-Agent Layer` - 6 edges
2. `Next.js Multi-Tab Dashboard` - 6 edges
3. `Pydantic Schemas` - 5 edges
4. `Storage Layer (SQLite & Vector Store)` - 4 edges
5. `Deterministic Regex Router` - 3 edges
6. `OpenRouter LLM Gateway` - 3 edges
7. `FastAPI Backend API` - 2 edges
8. `Deterministic-First, LLM-Augmented` - 2 edges
9. `Gmail API Ingestion Layer` - 1 edges
10. `ReceiptData Schema` - 1 edges

## Surprising Connections (you probably didn't know these)
- `Deterministic-First, LLM-Augmented` --rationale_for--> `Deterministic Regex Router`  [INFERRED]
  project.md → architecture.md
- `Next.js Multi-Tab Dashboard` --conceptually_related_to--> `Financial Statistics Tab`  [EXTRACTED]
  architecture.md → project.md
- `Next.js Multi-Tab Dashboard` --conceptually_related_to--> `Important Contacts Tab`  [EXTRACTED]
  architecture.md → project.md
- `Next.js Multi-Tab Dashboard` --conceptually_related_to--> `Meetings & Deadlines Tab`  [EXTRACTED]
  architecture.md → project.md
- `Next.js Multi-Tab Dashboard` --conceptually_related_to--> `Newsletters Tab`  [EXTRACTED]
  architecture.md → project.md

## Hyperedges (group relationships)
- **IndexLens Data Processing Pipeline** — architecture_gmail_api_ingestion, architecture_regex_router, architecture_openrouter_llm, architecture_storage_layer [EXTRACTED 1.00]
- **IndexLens Multi-Agent System** — architecture_supervisor_agent, architecture_extraction_agent, architecture_categorization_agent, architecture_anomaly_agent, architecture_digest_agent [EXTRACTED 1.00]

## Communities (13 total, 8 thin omitted)

### Community 0 - "Multi-Agent System & Agents"
Cohesion: 0.33
Nodes (6): Anomaly Agent, Categorization Agent, Weekly Digest Agent, Extraction Agent, Multi-Agent Layer, Supervisor Agent

### Community 1 - "Ingestion, Routing & Gateway"
Cohesion: 0.33
Nodes (6): Gmail API Ingestion Layer, OpenRouter LLM Gateway, Deterministic Regex Router, Redis Semantic Cache, Deterministic-First, LLM-Augmented, IndexLens Project

### Community 2 - "Next.js Multi-Tab Dashboard"
Cohesion: 0.33
Nodes (6): Next.js Multi-Tab Dashboard, Financial Statistics Tab, Important Contacts Tab, Meetings & Deadlines Tab, Newsletters Tab, Active Subscriptions Tab

### Community 3 - "Pydantic Extraction Schemas"
Cohesion: 0.40
Nodes (5): DeadlineData Schema, ExtractedEmail Schema, MeetingData Schema, Pydantic Schemas, ReceiptData Schema

### Community 4 - "Storage, Embeddings & Query Layer"
Cohesion: 0.50
Nodes (4): BGE-Small Local Embedding, FastAPI Backend API, Query Layer (SQL Stats + RAG), Storage Layer (SQLite & Vector Store)

## Knowledge Gaps
- **28 isolated node(s):** `IndexLens Architecture`, `Gmail API Ingestion Layer`, `ReceiptData Schema`, `MeetingData Schema`, `DeadlineData Schema` (+23 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 28 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **8 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Storage Layer (SQLite & Vector Store)` connect `Storage, Embeddings & Query Layer` to `Multi-Agent System & Agents`?**
  _High betweenness centrality (0.116) - this node is a cross-community bridge._
- **Why does `Multi-Agent Layer` connect `Multi-Agent System & Agents` to `Storage, Embeddings & Query Layer`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **Why does `Next.js Multi-Tab Dashboard` connect `Next.js Multi-Tab Dashboard` to `Storage, Embeddings & Query Layer`?**
  _High betweenness centrality (0.101) - this node is a cross-community bridge._
- **What connects `IndexLens Architecture`, `Gmail API Ingestion Layer`, `ReceiptData Schema` to the rest of the system?**
  _28 weakly-connected nodes found - possible documentation gaps or missing edges._