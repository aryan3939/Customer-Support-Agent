# OpenMetadata AI Agent

## Repository Documentation

### Index

- [1. What This Repository Does](#1-what-this-repository-does)
- [2. Core Capabilities](#2-core-capabilities)
- [3. Technology Stack](#3-technology-stack)
- [4. High-Level Architecture](#4-high-level-architecture)
- [5. Repository Layout](#5-repository-layout)
- [6. Runtime Configuration](#6-runtime-configuration)
- [7. Documentation Coverage Strategy](#7-documentation-coverage-strategy)
- [8. Ingestion Pipeline](#8-ingestion-pipeline)
- [9. Chunking Strategy](#9-chunking-strategy)
- [10. Embedding Pipeline](#10-embedding-pipeline)
- [11. Storage Layer](#11-storage-layer)
- [12. Retrieval Pipeline](#12-retrieval-pipeline)
- [13. Agent Workflow](#13-agent-workflow)
- [14. Interfaces](#14-interfaces)
- [15. How To Run](#15-how-to-run)
- [16. Evaluation](#16-evaluation)
- [17. Design Choices and Tradeoffs](#17-design-choices-and-tradeoffs)

This repository implements a backend-first AI assistant for OpenMetadata documentation. It ingests a curated but broad subset of `docs.open-metadata.org`, builds a searchable knowledge base, and answers natural-language questions through an agentic Retrieval-Augmented Generation (RAG) workflow using GPT-4o.

The focus of the project is the RAG system itself:

- reliable ingestion from a dynamic documentation site,
- structure-aware chunking,
- local embeddings,
- dense and sparse retrieval,
- query-time context expansion,
- agentic retrieval correction,
- grounded answer generation.

## 1. What This Repository Does

The system is designed to answer questions such as:

- how to deploy OpenMetadata,
- how to configure a connector,
- what a feature such as lineage, governance, or quality means,
- where a specific capability is described in the documentation.

Instead of answering from model memory alone, the repository builds a documentation knowledge base and forces the model to answer from retrieved context.

At a high level, the flow is:

1. scrape OpenMetadata documentation pages,
2. clean and normalize the content,
3. split the content into retrieval chunks,
4. embed and store those chunks,
5. classify user intent at query time,
6. route generic, out-of-scope, and ambiguous queries to dedicated response paths,
7. for documentation queries, run hybrid retrieval,
8. grade relevance and compute evidence strength,
9. rewrite and retry retrieval only when evidence is weak,
10. generate a grounded answer with citations.

## 2. Core Capabilities

The repository currently provides:

- offline ingestion of OpenMetadata documentation,
- two-stage Markdown-aware chunking,
- local embeddings with `all-MiniLM-L6-v2`,
- PostgreSQL + `pgvector` storage,
- semantic vector retrieval,
- PostgreSQL keyword retrieval,
- hybrid retrieval with reciprocal-rank fusion,
- small-to-big context expansion,
- intent classification and conditional routing,
- dedicated handling for generic, out-of-scope, and ambiguous queries,
- agentic document grading and query rewriting,
- evidence-scored rewrite and generation gating,
- CLI chat experience,
- optional FastAPI backend,
- retrieval evaluation scripts.

## 3. Technology Stack

The implementation is built around the dependencies listed in `requirements.txt`.

### 3.1 Ingestion and Parsing

- `crawl4ai`
- `httpx`
- `lxml`

These are used to fetch sitemap data, render Mintlify pages in a browser context, and work with the resulting document content.

### 3.2 LLM and Orchestration

- `langchain`
- `langchain-core`
- `langchain-community`
- `langchain-openai`
- `langchain-text-splitters`
- `langgraph`

These packages provide:

- prompt and message abstractions,
- model wrappers,
- text splitters,
- stateful graph orchestration for the agent workflow.

### 3.3 Embeddings

- `sentence-transformers`

Used to generate local embeddings with `all-MiniLM-L6-v2`.

### 3.4 Storage

- `supabase`
- `psycopg2-binary`

These are used for application-level access and direct schema setup against Supabase/PostgreSQL.

### 3.5 Runtime Interfaces

- `fastapi`
- `uvicorn[standard]`
- `rich`

Used for the HTTP API and the terminal chat interface.

### 3.6 Observability and Evaluation

- `langsmith`
- `tabulate`
- `ragas`
- `datasets`

These support tracing and evaluation workflows. They are useful for inspection and benchmarking, but the core runtime path does not depend on them.

## 4. High-Level Architecture

The system is split into three major layers.

### 4.1 Ingestion Layer

Responsible for building the knowledge base from OpenMetadata documentation.

Main modules:

- `src/ingestion/sitemap_parser.py`
- `src/ingestion/scraper.py`
- `src/ingestion/text_cleaner.py`
- `src/ingestion/chunker.py`
- `src/ingestion/ingest.py`

### 4.2 Storage and Retrieval Layer

Responsible for storing content, embeddings, indexes, and retrieval functions.

Main modules:

- `src/database/supabase_client.py`
- `src/database/vector_store.py`
- `src/database/text_search.py`
- `scripts/setup_db.py`

### 4.3 Agent and Application Layer

Responsible for user interaction, retrieval orchestration, answer generation, and session handling.

Main modules:

- `src/agent/graph.py`
- `src/agent/nodes.py`
- `src/agent/prompts.py`
- `src/main.py`
- `src/api/server.py`

### 4.4 Literal Workflows

Instead of textual descriptions, below are the literal workflows controlling the Agent logic and the offline ingestion pipeline.

#### Workflow 1: LangGraph Agent Runtime

```text
[User Query]
   |
   v
[classify_intent]
  |-------------------|------------------------|---------------------|
  | generic_meta      | out_of_scope           | ambiguous           | docs_qa
  v                   v                        v                     v
[generate_generic] [generate_out_of_scope] [clarify_question]    [retrieve]
                                         (Vector + Keyword + RRF)
                                                |
                                                v
                                     [grade_documents + evidence_score]
                                                |
                                                v
                                           [should_rewrite]
                                            |           |
                              weak evidence + retries left    generate
                                            |           |
                                            v           v
                                        [rewrite_query] [generate]
                                            |
                                            v
                                         [retrieve] (loop)
```

#### Workflow 2: Ingestion Pipeline

```text
[Sitemap XML]
      |
      v
[Filter by Version & Category]
      |
      v
[Fetch async via Crawl4AI]
      |
      v
[Clean Mintlify Artifacts & Headers]
      |
      v
[Content Hash Changed?]
   |                 |
   | No              | Yes
   v                 v
[Skip Page]      [Markdown Header Chunking]
                     |
                     v
                 [Recursive Size Chunking]
                     |
                     v
                 [Embed Chunks using all-MiniLM-L6-v2]
                     |
                     v
                 [Upsert to Supabase]
```

### 4.5 File Structure Explained

This section breaks down the physical layout of the OpenMetadata Agent repository functionality.

#### `src/agent/` - LangGraph State Machine

- **`state.py`**: Defines `AgentState` with messages, query, rewrite counters, intent metadata, and evidence score.
- **`prompts.py`**: Contains prompts for intent classification, generic/meta responses, out-of-scope redirects, clarification, grading, rewriting, and grounded generation.
- **`nodes.py`**: Implements `classify_intent`, `route_by_intent`, hybrid retrieval with RRF, relevance grading, evidence scoring, rewrite decisions, and branch-specific generation nodes.
- **`graph.py`**: Wires intent-first conditional routing plus the docs-only retrieve-grade-rewrite loop.

#### `src/ingestion/` - Scraping Pipeline

- **`sitemap_parser.py`**: Fetches and filters the original Sitemap URLs.
- **`scraper.py`**: Async DOM browser fetching via Crawl4AI.
- **`chunker.py`**: Implements the Split-by-Header then Recursive limit strategy.
- **`ingest.py`**: Orchestrates parsing -> embedding -> writing to DB.

#### `src/api/` and Core Modules

- **`server.py`**: FastAPI serving `/api/chat`.
- **`config.py`**: Central brain distributing `.env` variables via `Pydantic` settings classes.

### 4.6 Database Design Explained

```text
+-----------------------+              +-----------------------+
| sources               |              | documents             |
+-----------------------+              +-----------------------+
| id (uuid) primary key |<-------------| source_id (uuid) FK   |
| url (text)            | 1          N | content (text)        |
| title (text)          |              | embedding (vector)    |
| category (text)       |              | chunk_index (int)     |
| content_hash (text)   |              | metadata (jsonb)      |
+-----------------------+              +-----------------------+
```

The underlying pgvector database relies on exactly two interconnected tables.

1. **`sources` Table (The Page Level)**
   - Holds the macro context: `url`, `title`, `category`, and `content_hash`.
   - Before ingestion, new content hashes are compared against this table to safely skip unchanged pages, dramatically speeding up crawls.

2. **`documents` Table (The Chunk Level)**
   - Holds exactly what is retrieved: `content` and `embedding` (384-dimension vector).
   - Tied to `sources` via a `source_id` foreign key.
   - Importantly, it includes `chunk_index`, an integer denoting exactly where in the full document this sequential chunk lived. The agent queries `chunk_index - 1` and `chunk_index + 1` natively during query time to successfully reconstruct surrounding context on vector hits!

### 4.7 Workflow Usage Note

- Section `4.4` is the architecture view.
- Section `4.5` is the physical codebase layout.
- Section `4.6` describes schema logic.

## 5. Repository Layout

### 5.1 Root Files

- `requirements.txt`
  Dependency list.
- `.env.example`
  Environment variable template.
- `README.md`
  General quick-start documentation.
- `PROJECT_DOCUMENTATION.md`
  Root-level technical documentation for the repository.

### 5.2 `src/`

Primary application code.

- `src/config.py`
  Central runtime configuration.
- `src/main.py`
  CLI entry point.

### 5.3 `src/ingestion/`

Offline documentation ingestion pipeline.

### 5.4 `src/embeddings/`

Embedding model wrapper and batch embedding logic.

### 5.5 `src/database/`

Supabase client, vector retrieval wrapper, and keyword retrieval wrapper.

### 5.6 `src/agent/`

LangGraph state machine, prompts, and runtime retrieval/generation logic.

### 5.7 `src/api/`

Optional FastAPI layer for chat and monitoring endpoints.

### 5.8 `scripts/`

Operational scripts for:

- schema creation,
- ingestion runs,
- server startup,
- local smoke tests.

### 5.9 `eval/`

Evaluation scripts and golden query sets.

### 5.10 `docs/`

Additional deeper technical documents, including:

- `docs/engineering_guide.md`
- `docs/rag_pipeline.md`

## 6. Runtime Configuration

### 6.1 LLM Configuration

Current defaults:

- provider: `openai`
- model: `gpt-4o`
- temperature: `0.3`
- max tokens: `1024`
- base URL: `https://api.openai.com/v1`

The project uses an OpenAI-compatible wrapper (`ChatOpenAI`) while selecting the active backend through configuration.

### 6.2 Embedding Configuration

Current defaults:

- model: `all-MiniLM-L6-v2`
- dimensions: `384`
- device: `cpu`

### 6.3 Retrieval Configuration

Current defaults:

- `TOP_K = 5`
- `SIMILARITY_THRESHOLD = 0.5`
- `REWRITE_MAX_ATTEMPTS = 2`
- `EXPAND_CONTEXT = True`
- `CONTEXT_WINDOW = 1`
- `EVIDENCE_MIN_SCORE = 0.45`
- `INTENT_MIN_CONFIDENCE = 0.65`

These settings control not only retrieval breadth and similarity filtering, but also whether weakly supported answers should be rewritten or blocked in favor of safer fallback responses.

### 6.4 Chunking Configuration

Current defaults:

- `CHUNK_SIZE = 1500`
- `CHUNK_OVERLAP = 300`

### 6.5 Ingestion Configuration

Current defaults:

- docs version: `v1.12.x`
- max pages: `1000`
- concurrency: `10`
- categories:
  - `quickstart`
  - `deployment`
  - `how-to`
  - `connectors`
  - `developers`
  - `releases`
  - `concepts`

## 7. Documentation Coverage Strategy

The ingestion pipeline targets a broad but curated subset of the documentation rather than every possible page.

This keeps the knowledge base:

- focused on product-facing content,
- less noisy than a full blind crawl,
- cheaper and easier to maintain,
- better aligned with common user questions.

At the same time, the current configuration aims for broad practical coverage by ingesting all matching pages in the selected categories, which is roughly the entire filtered subset of the chosen documentation version.

## 8. Ingestion Pipeline

The ingestion pipeline turns live documentation into a retrieval-ready knowledge base.

### 8.1 Sitemap Discovery

`src/ingestion/sitemap_parser.py`:

- downloads the sitemap,
- filters URLs by target version,
- maps paths into documentation categories,
- removes noisy low-value CRUD-like suffixes,
- caps the final set if needed.

### 8.2 Scraping

`src/ingestion/scraper.py` uses Crawl4AI because OpenMetadata docs are Mintlify-based and heavily client-rendered. A plain static scraper would miss content or capture the wrong structure.

The scraper:

- runs in a browser context,
- extracts Markdown instead of raw HTML,
- excludes obvious navigation containers,
- removes overlay elements,
- batches requests using configurable concurrency.

### 8.3 Cleaning

Before chunking, the page body is cleaned to remove artifacts that would otherwise poison embeddings and retrieval.

Cleaning includes:

- trimming content between `"On this page"` and `"Was this page helpful?"`,
- removing Mintlify-generated empty links such as `[](url#anchor)`,
- removing empty headings,
- removing stray numbered lines,
- collapsing repeated blank lines.

### 8.4 Idempotent Ingestion

The pipeline stores a content hash per source page and skips unchanged pages by default. This makes repeated ingestion practical during iteration.

### 8.5 Ingestion Workflow

The ingestion run follows a fixed sequence:

1. Fetch the documentation sitemap.
2. Filter URLs by version and allowed category.
3. Scrape each selected page with Crawl4AI.
4. Clean the Markdown to remove navigation and template artifacts.
5. Split the cleaned content into chunks.
6. Generate embeddings for every chunk.
7. Upsert the page metadata into the `sources` table.
8. Store the chunk records and embeddings in the `documents` table.

## 9. Chunking Strategy

Chunking is implemented in `src/ingestion/chunker.py` and is one of the most important design decisions in the repository.

The current chunker uses a two-stage structure-aware pipeline:

1. split first by section headers,
2. split oversized sections recursively,
3. preserve heading metadata on every chunk,
4. expand locally at retrieval time with surrounding chunks.

### 9.1 Current Strategy

The live strategy is:

- `MarkdownHeaderTextSplitter` on `##`, `###`, and `####`
- `RecursiveCharacterTextSplitter` only when a section exceeds `CHUNK_SIZE`
- chunk size: `1500` characters
- overlap: `300` characters
- context expansion: `+-1` surrounding chunks at retrieval time

This gives the system section-aware chunk boundaries while still keeping chunk size controlled for embeddings and retrieval.

### 9.2 Why Header + Recursive Works

Header-based splitting prevents chunks from blending unrelated sections together. Recursive splitting handles the oversized sections that remain after structural splitting.

This matters for documentation because:

- headings often encode intent,
- adjacent subsections may discuss very different concepts,
- technical pages mix prose, lists, and code blocks,
- broad queries need enough scope, while specific queries need precision.

### 9.3 Chunking Experiments

During iteration, three broad chunking directions were considered:

#### A. Pure Recursive Chunking

This is the simplest baseline: split the entire page only by recursive separators and fixed chunk sizes.

Result:

- easiest to implement,
- but the weakest retrieval behavior for this dataset,
- because chunks can cross section boundaries and blend unrelated topics.

This was the worst-performing direction conceptually for documentation QA and is not the current strategy.

#### B. Small-to-Big Retrieval

This pattern retrieves small chunks first and then expands to larger local context. In the current codebase, this is partially realized through retrieval-time context expansion using surrounding chunks.

Result:

- strong retrieval precision from smaller units,
- better answer completeness after expansion,
- especially useful when adjacent chunks contain prerequisite details or step sequences.

#### C. Header + Recursive Chunking

This became the final chunking choice.

Result:

- better than pure recursive for structured docs,
- safer section boundaries,
- stronger embeddings because heading context remains tied to content,
- more stable behavior across both specific and broad queries.

### 9.4 What We Learned From the Chunking Experiments

The chunking experiments taught us that chunk size depends on the data shape and the query patterns:

- `400` chars:
  Too granular for documentation. Broad queries such as "What connectors are supported?" fail because no single tiny chunk covers enough related information.
- `2000` chars:
  Usable, but sections can mix multiple topics, which dilutes embeddings and weakens retrieval focus.
- `1500` chars with header-based splitting:
  Best overall tradeoff. Headers prevent cross-section contamination, while `1500` characters keep enough context for both broad and specific queries. Retrieval-time context expansion with surrounding chunks handles cases where adjacent information is needed.

### 9.5 Chunking Decision Summary

| Setting           | Value                                           | Why                                                                                                    |
| ----------------- | ----------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| Chunking          | Header + Recursive, `1500` chars, `300` overlap | Headers prevent cross-section contamination, `1500` is a strong balance for broad and specific queries |
| Pages             | All filtered pages, about `917`                 | Broad coverage reduces misses caused by absent pages                                                   |
| Concurrency       | `10`                                            | Good ingestion throughput without excessive memory pressure                                            |
| TOP_K             | `5`                                             | Standard retrieval depth, with deduplication in evaluation                                             |
| Context Expansion | `+-1` surrounding chunks                        | Reconstructs local context at retrieval time                                                           |
| Eval Ranking Unit | Deduplicated by source URL                      | Matches the real agent behavior better than raw chunk-only ranking                                     |

## 10. Embedding Pipeline

`src/embeddings/embedding_service.py` wraps the embedding model in a singleton so the model is loaded once and reused across the application.

### 10.1 Embedding Model

Current embedding configuration:

- model: `all-MiniLM-L6-v2`
- dimensions: `384`
- device: `cpu`

The service validates the embedding dimensionality at startup to ensure the configured vector size matches the model output.

### 10.2 How Embeddings Are Used

Embeddings are created in two places:

- during ingestion for every stored chunk,
- at query time for the user question.

The ingestion flow uses batch embedding for throughput, while runtime query embedding uses single-text encoding.

### 10.3 Why Local Embeddings Were Chosen

Local embeddings are a good fit here because:

- the corpus is moderate in size,
- cost control matters,
- deterministic behavior is useful during iteration,
- `384` dimensions are efficient to store and search with `pgvector`.

## 11. Storage Layer

The repository uses Supabase/PostgreSQL with `pgvector`. This gives the project one integrated system for structured data, dense retrieval, sparse retrieval, and chunk adjacency lookup.

### 11.1 Core Tables

#### `sources`

Stores page-level metadata:

- unique URL,
- title,
- section category,
- content hash,
- raw cleaned content,
- active flag,
- timestamps.

This is the parent record for a documentation page.

#### `documents`

Stores retrieval units:

- chunk content,
- embedding vector,
- chunk index,
- metadata JSON,
- source foreign key.

Each row represents one chunk that can be retrieved independently.

#### `conversations` and `messages`

These exist as future-ready persistence tables. The current runtime API uses in-memory sessions, but the schema already leaves space for durable chat persistence later.

### 11.2 Why This Database Design Works

This design cleanly separates:

- page-level identity and lifecycle in `sources`,
- chunk-level retrieval units in `documents`.

That separation helps with:

- idempotent re-ingestion,
- source-level deduplication,
- chunk-order-based expansion,
- future metadata filtering.

### 11.3 Indexing Strategy

The retrieval path depends on several important indexes:

- HNSW index on `documents.embedding`
- GIN index on `to_tsvector('english', content)`
- `(source_id, chunk_index)` index for fast chunk-neighbor lookup
- source-level indexes for category and active status

Why these matter:

- HNSW makes vector retrieval practical at query time.
- GIN keeps keyword search efficient.
- chunk-order indexing makes context expansion cheap and predictable.

## 12. Retrieval Pipeline

The live retrieval logic is implemented in `src/agent/nodes.py`, with database support in `src/database/vector_store.py` and `src/database/text_search.py`.

### 12.1 Retrieval Goals

The retrieval system is designed to handle both:

- semantic questions, where the user does not use exact documentation wording,
- exact-term questions, where literal product terms matter a lot.

That is why the runtime path uses hybrid retrieval instead of vector-only retrieval.

### 12.2 Step-by-Step Retrieval Flow

For documentation queries, the `retrieve` node does the following:

1. embed the user query,
2. run vector similarity search through `match_documents`,
3. expand vector hits to parent context using `get_surrounding_chunks`,
4. run keyword search through `keyword_search`,
5. merge both result lists with reciprocal-rank fusion,
6. return the fused top-k results to the grader.

### 12.3 Vector Retrieval

Vector retrieval is responsible for semantic recall.

It helps when:

- the user paraphrases documentation terms,
- the query is concept-based,
- the most relevant page does not share many exact words with the question.

### 12.4 Keyword Retrieval

Keyword retrieval is responsible for exact-term recall.

It helps when:

- the user asks for a named connector,
- the query includes an exact setting name,
- the question uses literal doc terminology,
- vector retrieval alone might miss precise lexical matches.

### 12.5 Small-to-Big Retrieval

The repository uses a small-to-big pattern at runtime:

- search starts from chunk-level units,
- top vector matches are expanded with surrounding chunks,
- generation sees a more coherent local section rather than a tiny isolated fragment.

This improves answer quality for step-by-step docs and neighboring explanatory text.

### 12.6 Reciprocal-Rank Fusion

Vector and keyword results are merged using reciprocal-rank fusion (RRF).

Conceptually:

- high ranks in either retriever contribute to the final score,
- the system does not need to normalize vector similarity and keyword rank into the same scale,
- documents that perform well in both retrievers naturally rise higher.

This is a practical and robust hybrid strategy for this size of project.

### 12.7 Retrieval-Time Context Expansion

The configuration currently uses:

- `EXPAND_CONTEXT = True`
- `CONTEXT_WINDOW = 1`

That means the system fetches one chunk before and one chunk after a vector hit when available. This is enough to recover local surrounding context without flooding the generator with an entire page.

## 13. Agent Workflow

The agent is implemented as a LangGraph state machine in `src/agent/graph.py`.

### 13.1 Graph Nodes

The major nodes are:

- `classify_intent`
- `route_by_intent` (conditional edge function)
- `retrieve`
- `grade_documents`
- `rewrite_query`
- `generate`
- `generate_generic`
- `generate_out_of_scope`
- `clarify_question`

`generate_direct` is retained as a backward-compatible alias to the generic branch.

### 13.2 Why a Graph Instead of a Linear Chain

A linear chain would retrieve once and answer immediately. This is often too brittle for documentation QA because retrieval can fail for vocabulary reasons even when the answer exists in the corpus.

The graph improves resilience by:

- filtering weak retrieval results,
- retrying with a rewritten query,
- avoiding immediate failure after one poor retrieval pass.

### 13.3 Intent Classification and Routing

The runtime now starts with explicit intent classification in `classify_intent`.

Intent labels:

- `docs_qa`: OpenMetadata documentation question
- `generic_meta`: greeting, capability, or assistant-help query
- `out_of_scope`: unrelated request
- `ambiguous`: too vague to route safely

Routing behavior:

- `generic_meta` -> `generate_generic`
- `out_of_scope` -> `generate_out_of_scope`
- `ambiguous` -> `clarify_question`
- `docs_qa` -> retrieval pipeline

This avoids wasting retrieval calls on non-documentation interactions while preserving robust RAG behavior for true docs queries.

### 13.4 Relevance Grading and Evidence Scoring

After retrieval, each candidate chunk is graded with a binary yes/no relevance check.

In addition, the agent computes an `evidence_score` based on:

- top semantic similarity among remaining docs,
- relevant-doc coverage relative to `TOP_K`,
- keyword or hybrid retrieval signal.

Why this matters:

- hybrid retrieval can still surface noisy results,
- grading reduces context contamination before generation,
- evidence scoring prevents confident-sounding answers when support is weak.

### 13.5 Query Rewriting

If evidence is weak and rewrite budget remains, the system rewrites the query and loops back to retrieval.

Current rewrite limit:

- `REWRITE_MAX_ATTEMPTS = 2`

This is especially useful when user terminology and documentation terminology differ.

### 13.6 Final Generation

Generation now has branch-specific behavior:

- `generate` (docs path): runs only when evidence is strong enough, answers from retrieved context, and includes citations.
- low-evidence docs fallback: asks the user to rephrase with specific OpenMetadata terms instead of producing a weakly grounded answer.
- `generate_generic`: concise capability/help response.
- `generate_out_of_scope`: polite redirect to OpenMetadata scope.
- `clarify_question`: one targeted clarifying question with concrete options.

The prompts live in `src/agent/prompts.py`, which keeps behavior centralized and auditable.

### 13.7 Agent Workflow Diagram

```text
[User Query]
  |
  v
[classify_intent]
  |-------------------|------------------------|---------------------|
  | generic_meta      | out_of_scope           | ambiguous           | docs_qa
  v                   v                        v                     v
[generate_generic] [generate_out_of_scope] [clarify_question]    [retrieve]
                                         (Vector + Keyword + RRF)
                                                |
                                                v
                                     [grade_documents + evidence_score]
                                                |
                                                v
                                           [should_rewrite]
                                            |           |
                              weak evidence + retries left    generate
                                            |           |
                                            v           v
                                        [rewrite_query] [generate]
                                            |
                                            v
                                         [retrieve] (loop)
```

## 14. Interfaces

The repository provides two main runtime interfaces.

### 14.1 CLI

`src/main.py` provides a terminal assistant with:

- interactive chat,
- conversation reset,
- help output,
- database stats display.

This is the fastest way to test and demo the repository.

### 14.2 FastAPI Server

`src/api/server.py` exposes:

- `GET /api/health`
- `GET /api/stats`
- `POST /api/chat`
- `POST /api/chat/reset`

The API uses in-memory session tracking via `session_id`, so follow-up questions remain contextual inside the same session.

## 15. How To Run

### 15.1 Prerequisites

- Python 3.11+
- a Supabase project
- an API key for the configured LLM provider
- optional LangSmith credentials

### 15.2 Environment Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install Crawl4AI browser dependencies:

```bash
crawl4ai-setup
```

### 15.3 Environment Variables

Start from `.env.example`.

The main required values are:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_DB_URL`
- one provider key matching the configured provider in `src/config.py`

Optional tracing values:

- `LANGCHAIN_API_KEY`
- `LANGCHAIN_ENDPOINT`
- `LANGCHAIN_PROJECT`

### 15.4 Create the Database Schema

```bash
python scripts/setup_db.py
```

### 15.5 Ingest Documentation

```bash
python scripts/run_ingestion.py
```

Useful variants:

```bash
python scripts/run_ingestion.py --force
python scripts/run_ingestion.py --clean
```

### 15.6 Run the CLI

```bash
python -m src.main
```

### 15.7 Run the API

```bash
python scripts/run_server.py
```

## 16. Evaluation

The repository includes an `eval/` directory for measuring retrieval quality and, optionally, end-to-end answer quality.

The current practical focus is on **retrieval evaluation**, because retrieval quality is the main dependency for good answer quality in this system.

### 16.1 Current Evaluation Files

- `eval/golden_queries.py`
  Contains representative documentation questions and expected source URL patterns.
- `eval/run_eval.py`
  Runs retrieval evaluation using the stored vectors.
- `eval/run_ragas.py`
  Exists for answer-level evaluation, but it is not the primary focus of this document.

### 16.2 What the Retrieval Evaluation Measures

The retrieval evaluation uses golden queries and checks whether relevant source pages appear in the retrieved results.

Main metrics:

- `HR@K`:
  Hit Rate at K. Measures whether at least one relevant source appears in the top-k results.
- `MRR@K`:
  Mean Reciprocal Rank. Rewards systems that return the first relevant result earlier in the ranking.

These are appropriate first-line metrics for this repository because they directly measure whether retrieval is surfacing the right documentation before generation even begins.

### 16.3 Why the Evaluation Deduplicates by Source URL

The live agent may retrieve multiple chunks from the same documentation page. If evaluation only looked at raw chunks, ranking quality would be distorted by chunk duplication.

To better match the real runtime behavior, the retrieval evaluation:

- over-fetches chunk-level vector results,
- deduplicates by `source_url`,
- keeps the strongest match per source,
- then evaluates ranking over unique sources.

This is a more realistic measurement for a documentation assistant than raw chunk-only ranking.

### 16.4 Why `TOP_K = 5`

The current evaluation uses `TOP_K = 5` because:

- it matches the live retrieval depth,
- it is a standard practical retrieval budget,
- it keeps the context passed to the generator reasonably focused,
- it provides a clean baseline for comparing strategy changes.

### 16.5 Evaluation Settings That Emerged From Experimentation

| Setting           | Value                                           | Why                                                    |
| ----------------- | ----------------------------------------------- | ------------------------------------------------------ |
| Chunking          | Header + Recursive, `1500` chars, `300` overlap | Strongest balance of precision and context             |
| Pages             | All filtered pages, about `917`                 | Reduces misses caused by incomplete corpus coverage    |
| Concurrency       | `10`                                            | Good throughput without excessive memory cost          |
| TOP_K             | `5`                                             | Stable practical retrieval depth                       |
| Context Expansion | `+-1` surrounding chunks                        | Enough local expansion without excessive context bloat |
| Eval Unit         | Deduplicated by source URL                      | Better match to actual agent behavior                  |

### 16.6 What We Learned From Evaluation and Experiments

The current experiments suggest:

- pure recursive chunking is the weakest fit for this dataset,
- broad coverage matters because missing pages create artificial retrieval failures,
- header-aware chunking helps both retrieval quality and interpretability,
- local context expansion improves answer readiness without requiring page-level retrieval,
- evaluation must match runtime behavior, especially around deduplication.

## 17. Design Choices and Tradeoffs

The repository intentionally favors clarity and maintainability over unnecessary infrastructure complexity.

### 17.1 Why Agentic RAG Instead of a Simple RAG Chain

Because documentation questions often fail on the first retrieval attempt due to vague or user-specific wording. The retrieve-grade-rewrite loop gives the system a second chance before answering.

### 17.2 Why Local Embeddings

Because they reduce cost, simplify iteration, and are sufficient for a focused documentation corpus.

### 17.3 Why PostgreSQL-Based Retrieval

Because this scale benefits from one integrated storage layer that supports dense retrieval, sparse retrieval, and chunk adjacency without introducing a separate search platform.

### 17.4 Why Curated but Broad Documentation Coverage

Because targeted ingestion keeps retrieval cleaner than a blind full-site dump, while broad filtered coverage reduces misses from absent pages.
