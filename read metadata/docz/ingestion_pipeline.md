# Documentation Ingestion Pipeline

The initial hurdle to building a high-quality RAG system is parsing dynamic Web Content (SPAs built with React or heavily JavaScript-rendered static sites like Mintlify) into normalized text segments.

## 1. Crawl4AI Configuration (`scraper.py`)

OpenMetadata documentation is hosted on Mintlify. Mintlify aggressively uses client-side rendering. Using traditional scrapers like `BeautifulSoup` wrapped around Python `requests` returns a mostly empty DOM tree containing only Javascript bundles.

### Solution: Async Playwright & Crawl4AI
-   **Why `AsyncWebCrawler`**: Crawl4AI spins up a headless Chromium instance, executes the React hydrate cycle, and extracts the fully rendered DOM.
-   **Concurrency**: Defined in `src/config.py` as `IngestionConfig.CONCURRENCY` (10 instances default). The crawler groups URLs into batches, processing 10 async requests natively without overwhelming the memory.
-   **Output Format**: We fetch the raw `markdown` string version of the DOM, not the HTML.

## 2. Deterministic Content Parsing

Mintlify pages wrap actual documentation content inside heavy navigational UI components (Sidebars, Top Navigation, Table of Contents). Extracting by `<article>` or `<div class="content">` fails frequently because Mintlify class names are dynamically generated (e.g., hash outputs like `css-1x1s2p`).

### Boundary Detection
We shifted from a CSS-selector-based extraction to **String Boundary Detection**:
1.  **Start Boundary**: Search for the exact string `"On this page\n"` followed by the `* [Link](url)` TOC list. The documentation content *always* starts directly beneath this block.
2.  **End Boundary**: Search for the exact string `"Was this page helpful?"`. The footer begins here.

This `text[start_idx:end_idx]` slice extracts pure documentation content 100% reliably.

## 3. Dealing With Markdown Artifacts (`text_cleaner.py`)

Mintlify's Markdown generation explicitly inserts invisible anchor links (`[](url#heading)`) before every major `H1`-`H4` tag on the page to facilitate copyable URL fragment links.

### The Problem With Regex for `[](url)`
Initially, we used the pattern `re.sub(r'\[\]\([^)]*\)', '', content)`.
However, Python regex behavior on multi-line literal `[]` segments coupled with trailing whitespaces proved fragile across OS environments. It often left dangling `[]` fragments or stripped valid Markdown links entirely.

### The Character-Level Scanner Fix
We authored a bespoke `strip_empty_links()` function:
-   It uses a fast O(N) `while` loop over the string length.
-   It aggressively matches the literal `[` `]` `(` character sequence.
-   It tracks parenthesis depth `(` and `)`, robustly consuming the full URL block regardless of nested characters.
-   It emits a sanitized string that is perfectly clean for vector chunking.

## 4. Chunking with overlapping context (`chunker.py`)

LLMs struggle with context limits. We chunk our Markdown into smaller logical bites:
-   **Chunk Size**: 2000 Characters.
-   **Overlap Size**: 400 Characters.
-   **The Separator Priority**: Rather than splitting evenly mid-sentence, the LangChain `RecursiveCharacterTextSplitter` respects a hierarchy: `\n### ` -> `\n\n` -> `.` -> ` `

This guarantees that a heading "Connecting to Snowflake" and the immediate paragraph instruction beneath it are kept tightly coupled in the same Chunk Embedding.
