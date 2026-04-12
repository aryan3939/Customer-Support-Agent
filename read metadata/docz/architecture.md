# System Architecture

This document provides a detailed overview of the OpenMetadata AI Agent architecture.

## High-Level Overview

The system is designed as a Retrieval-Augmented Generation (RAG) pipeline with an agentic routing layer. It consists of three primary components:

1.  **Ingestion & Processing Layer (Python Scripts)**
2.  **Storage Layer (Supabase / PostgreSQL)**
3.  **Application & Agent Layer (FastAPI & LangGraph)**

---

## 1. Ingestion & Processing Layer
Located primarily in `src/ingestion/`. This layer runs offline to populate the knowledge base.

### 1.1 Crawler (`scraper.py`)
-   **Tool:** Crawl4AI
-   **Strategy:** Bypasses client-side rendering issues by crawling full pages and extracting raw Markdown.
-   **Concurrency:** Configurable (e.g., 10 parallel browsers) using `asyncio` to speed up processing of 900+ pages.
-   **Cleaning Pipeline:** Implements a multi-stage filtering process:
    1.  **Boundary Detection:** Locates "On this page" and "Was this page helpful?" strings to extract only the core documentation body, discarding navigation sidebars and footers.
    2.  **Artifact Removal:** Uses a custom character-level scanner (`strip_empty_links` in `text_cleaner.py`) to flawlessly remove Mintlify's injected `[](url#anchor)` tags, avoiding regex edge cases.

### 1.2 Chunker (`chunker.py`)
-   **Tool:** LangChain `RecursiveCharacterTextSplitter`
-   **Separators:** Custom Markdown-aware separators (`["\n## ", "\n### ", "\n\n", "\n", " "]`).
-   **Purpose:** Ensures paragraphs and code blocks remain intact. Small overlaps (e.g., 400 chars) prevent context loss at boundaries.

---

## 2. Storage Layer
Located in `scripts/setup_db.py` and `src/database/`.

### 2.1 Database Setup
-   **Platform:** Supabase (PostgreSQL 15+).
-   **Extensions:** Requires `pgvector` for semantic search and `pg_trgm` for robust text matching.

### 2.2 Core Tables
-   `sources`: Stores page metadata (URL, Category, raw Hash).
-   `documents`: Stores the individual text chunks and their 384-dimensional `embedding`.

### 2.3 Retrieval RPCs (Remote Procedure Calls)
All similarity calculations happen *inside* the database for maximum efficiency.
-   `match_documents`: Uses Cosine Distance (`<=>`) to find chunks closest to the user's query vector.
-   `keyword_search`: Uses traditional PostgreSQL Full-Text Search (FTS) with `to_tsvector` and `websearch_to_tsquery` to provide an exact-match fallback.

---

## 3. Application & Agent Layer
Located in `src/api/` and `src/agent/`.

### 3.1 LLM Configuration (`src/config.py`)
-   **Provider:** OpenRouter.
-   **Model:** `nvidia/nemotron-3-super-120b-a12b:free` (120B parameter MoE model).
-   **Embeddings:** `all-MiniLM-L6-v2` via `sentence-transformers` running locally on the CPU.

### 3.2 LangGraph State Machine (`src/agent/graph.py`)
Instead of a linear chain, the AI operates as a cyclical graph:
1.  **Route:** Determines if the query needs RAG or is just a greeting.
2.  **Retrieve:** Calls the Supabase RPCs via `EmbeddingService`.
3.  **Grade:** The LLM evaluates the relevance of the retrieved chunks.
4.  **Rewrite:** If chunks are poor, the LLM rewrites the query and loops back to **Retrieve**.
5.  **Generate:** Synthesizes the final answer with forced citations.

### 3.3 FastAPI Server (`src/api/server.py`)
-   Stateful API. It maintains an in-memory `SessionManager`. 
-   When `POST /api/chat` is called with a `session_id`, it retrieves that specific LangGraph `ChatAgent` instance, preserving the multi-turn conversation history.
-   Provides endpoints for Health and Database Stats.
