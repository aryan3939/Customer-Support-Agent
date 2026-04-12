# LangGraph Agent Design

The core reasoning logic of the OpenMetadata Agent is handled by LangGraph (`src/agent/graph.py`), which models the RAG process as a cyclic state machine.

## The Agent State (`src/agent/state.py`)

All nodes in the graph read and write to a shared `TypedDict` state:
-   **messages**: A combined list of `HumanMessage` and `AIMessage` representing the conversation history. It uses LangGraph's `add_messages` reducer to automatically append new messages.
-   **retrieved_docs**: A list of dictionaries returned from the Database RPC.
-   **query**: The string currently being processed. If the agent rewrites the query, this string updates.
-   **rewrite_count**: An integer preventing infinite loops during the rewrite phase. Max 2 attempts.

---

## Node Explanations (`src/agent/nodes.py`)

### 1. `route_query` (Conditional Edge)
-   **Logic**: Before doing expensive database lookups, check if the query is a simple greeting ("hi", "hello", "thanks").
-   **Action**: Routes to `generate_direct` if matched, otherwise routes to `retrieve`.

### 2. `retrieve`
-   **Logic**: Instantiates the `EmbeddingService`, embeds the `state["query"]`, and searches the database.
-   **Action**: Overwrites `state["retrieved_docs"]` with the top 5 closest matches.

### 3. `grade_documents`
-   **Prompt Name**: `GRADER_PROMPT`
-   **Logic**: For every document returned, the LLM is asked a binary question: "Is this document relevant to answering the user's question? Evaluate strictly with 'yes' or 'no'."
-   **Action**: Filters the `state["retrieved_docs"]` list, removing hallucinations or low-quality semantic matches.

### 4. `should_rewrite` (Conditional Edge)
-   **Logic**: Examines the length of the filtered `retrieved_docs` array. If it is empty (meaning all retrieved docs were graded 'no' by the LLM), and `rewrite_count < 2`, it routes to the rewriting node.
-   **Action**: Routes to `rewrite_query` OR `generate`.

### 5. `rewrite_query`
-   **Prompt Name**: `REWRITE_PROMPT`
-   **Logic**: The LLM acts as an experienced search engine user. It rewrites ambiguous statements into highly specific queries containing platform-centric keywords (e.g., transforming "tracking tables" into "Data Lineage configuration table metadata").
-   **Action**: Overwrites `state["query"]` and increments `rewrite_count`. The graph logically loops back to `retrieve`.

### 6. `generate` & `generate_direct`
-   **Prompt Name**: `GENERATE_PROMPT` & `SYSTEM_PROMPT`
-   **Logic**: The context chunks are concatenated into a large prompt block string format `[Source: title](url) \n content`. The LLM synthesizes an answer strictly from this block.
-   **Rules Enforced**: Must output Markdown, must cite source links, and must politely decline answering non-OpenMetadata questions.

---

## Why a Cyclic Graph?

Traditional RAG (like LangChain's basic RetrievalQA chain) is brittle. If the initial vector search fails because the user used poor terminology, the LLM hallucinates or says "I don't know."

By introducing **Self-Reflection (Grading)** and **Self-Correction (Rewriting)** in a loop, the agent has multiple chances to find the correct data before returning a final answer to the user. This dramatically increases both the Recall rate and User Trust. 
