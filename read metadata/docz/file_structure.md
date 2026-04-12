# Project File Structure

This document provides a highly detailed breakdown of the OpenMetadata Agent repository. Every folder and major file is described along with its specific usage, purpose, and relationship to the rest of the application.

---

## Root Level Files

| File | Purpose |
|------|---------|
| **`README.md`** | The front door to the project. Contains the system architecture, quick start setup commands, and explanation of design decisions. |
| **`PROJECT_DOCUMENTATION.md`** | Technical project documentation covering core capabilities, tech stack, and evaluation methodology. |
| **`requirements.txt`** | Python dependencies. Designed to support crawling, LangChain, Supabase, API serving, and local evaluation. |
| **`.env.example`** | Security template for environment variables (Supabase keys, LLM provider API keys, LangSmith tracking). **Never commit the real `.env`**! |
| **`.dockerignore`** | Prevents large local virtual environments (`venv/`) and credentials from bleeding into container images during deployment. |
| **`.gitignore`** | Ignore directives to keep SQLite DBs, Python caches (`__pycache__`), virtual environments, and secrets out of version control. |

---

## 📂 `src/` - Core Runtime Application

The `src/` directory contains all business logic related to fetching, storing, and conversing with data. It is modularized by functionality.

### **`src/` Root**
- **`config.py`**: The definitive central brain for configuration. Wraps `.env` files and distributes system constants (chunk sizes, specific models like `LLMConfig.MODEL = "gpt-4o"`, and context configurations) through Python classes.
- **`main.py`**: The Rich-based interactive Terminal Command-Line Interface (CLI). Allows developers to quickly chat with the agent or query for DB stats without starting the API server.

---

### 📂 `src/agent/` - LangGraph State Machine
This dictates the "Agentic" part of our RAG.

- **`state.py`**: Defines the shared `AgentState` schema holding messages, retrieved context, the current evaluation `query`, and the `rewrite_count` (which caps retry loops).
- **`prompts.py`**: Contains all LLM system prompts. Separates instructions rigidly (`SYSTEM_PROMPT` handles rules, `GRADER_PROMPT` checks relevancy, and `GENERATE_PROMPT` frames answers format).
- **`nodes.py`**: Contains all execution steps for the LangGraph state machine. Highlights include the `retrieve` node (which handles **Reciprocal Rank Fusion** combining semantic and keyword searches) and the `grade_documents` node.
- **`graph.py`**: The orchestrator. It wires the nodes together into a cyclical graph, establishes entry and exit paths, and wraps the compiled graph in the `ChatAgent` class to maintain history between conversation turns.
- **`tools.py`** (Optional / Future usage): Wraps basic python methods like keyword searches inside rigid descriptions if LangGraph is run exclusively in function/tool-calling mode instead of rigid loops.

---

### 📂 `src/api/` - Web Server (FastAPI)
Exposes the agent to web consumption.

- **`server.py`**: The FastAPI framework. It exposes `/api/chat` for interactions, `/api/stats`, and `/api/health`. Includes an in-memory `SessionManager` so distinct users have distinct conversation threads.

---

### 📂 `src/database/` - Postgres / Supabase
The data access layer interacting directly with pgvector.

- **`supabase_client.py`**: Initializes the global singleton Supabase client using stored keys, enforcing fail-fast behaviors if credentials are missing.
- **`vector_store.py`**: Complex wrapper bridging Python and pgvector RPCs. Used to execute semantic inserts (`embed_batch`), `match_documents` queries, and delete-and-refresh behaviors during re-ingestion.
- **`text_search.py`**: Executes the PostgreSQL tsvector exact-match queries directly against the `keyword_search` RPC function, returning data ready to be merged linearly.

---

### 📂 `src/embeddings/` - NLP Modeling
Translating plain text into mathematical space.

- **`embedding_service.py`**: Wraps `sentence-transformers` (`all-MiniLM-L6-v2`) in a singleton pattern so the 384-dimension local model is loaded only once per session into CPU/GPU memory, keeping processing incredibly fast and free.

---

### 📂 `src/ingestion/` - Scraping & Chunking Pipeline
The offline pipeline required to build the knowledge base.

- **`sitemap_parser.py`**: Fetches the global OpenMetadata `sitemap.xml`, extracts URLs matching the specified `v1.12.x` API docs, and maps URLs to distinct logical categories.
- **`scraper.py`**: Wraps **Crawl4AI**. Fetches docs in parallel async browser processes, successfully interpreting complex client-rendered React/Mintlify pages into raw Markdown.
- **`text_cleaner.py`**: Removes boilerplate. Eliminates headers, footers, repeated newlines, and empty Mintlify artifacts before attempting to parse meaning.
- **`chunker.py`**: Splits clean Markdown intelligently. Primarily splits at headings via `MarkdownHeaderTextSplitter`, then limits excessively large chunks recursively using `RecursiveCharacterTextSplitter`.
- **`ingest.py`**: The grand orchestrator tying the `.ingestion` folder together. Identifies new pages natively, parses them, encodes vectors, uploads to Supabase, and drops old references.

---

### 📂 `src/utils/` - Shared Utilities
- **`logger.py`**: Configures a global Rich-compatible Python logger for consistent formatting (timestamps, log levels) across the full solution.

---

## 📂 `scripts/` - Direct Executable Commands

Scripts to bootstrap, maintain, or interact manually with the platform.

| Script | Explanation |
|--------|-------------|
| **`setup_db.py`** | Written heavily using `psycopg2`. Runs DDL queries explicitly to drop or create the required Extensions (`pgvector`, `pg_trgm`), schemas, tables (`sources`, `documents`), and complex Postgres RPC match functions. |
| **`run_ingestion.py`** | Terminal interface to `src.ingestion.ingest`. Use `--force` to re-scrape even correctly hashed pages, and `--clean` to wipe existing tables. |
| **`run_server.py`** | Terminal interface to invoke the FastAPI server via Uvicorn. Pass `--port` or `--reload` to configure hot reloading directly. |
| **`test_chunker.py`** | Developer sandbox for validating how specific strings respond to the Markdown separator criteria prior to ingestion. |
| **`test_scrape.py`** | Developer sandbox for validating Crawl4AI CSS selectors and Markdown cleanup operations on a single dynamic page. |

---

## 📂 `eval/` - Evaluation and Quality Assurance

Houses our benchmark frameworks for objective verification.

| Script | Explanation |
|--------|-------------|
| **`golden_queries.py`** | Contains static user questions and exactly which subset of `docs.open-metadata` URLs *should* be answered with for manual verification. |
| **`run_eval.py`** | The **Offline** retrieval tester. Extracts the target `golden_queries`, forces a vector/keyword search, and generates raw **Hit Rate (HR@K)** and **Mean Reciprocal Rank (MRR@K)** to quantify how effectively ingestion surfaces correct snippets. |
| **`run_ragas.py`** | The **Online** RAG QA. Actually simulates Agent behavior fully. Generates answers with the chosen model, then prompts **GPT-4o** dynamically via RAGAS to output quantifiable metrics like **Faithfulness** and **Answer Relevancy**. |
| **`eval_report.md`** | Generated benchmark artifact describing exactly how our generation scored mathematically on the latest eval run. |

---

## 📂 `docs/` - Extensional Knowledge

The project's deeper architectural brain.

| Document | Explanation |
|----------|-------------|
| **`engineering_guide.md`** | **Mandatory Reading for Contributors.** Contains over 6,000 lines outlining trade-offs, design philosophies, operational guidelines, and system mapping for edge cases (e.g. why hybrid was chosen, or why the fallback rewrites have a limit of 2). |
| **`rag_pipeline.md`** | Simple, focused walkthrough detailing purely the chunking logic parameters chosen. |
| **`file_structure.md`** | *This explicitly formatted file.* |
