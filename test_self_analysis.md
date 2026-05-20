Now I have a comprehensive understanding of the entire ctx-builder project. Let me compile the analysis.

---

## Architecture Analysis: ctx-builder

### 1. PROJECT SUMMARY

**ctx-builder** is a Python CLI tool and MCP server that collects and builds AI-ready context from codebases. It scans repositories, parses source code into ASTs, builds dependency graphs, and generates structured context documents (8 sections) for LLM-based code review, refactoring, and analysis.

- **Language**: Python 3.12+
- **Scale**: ~15 source files (core), plus 6 external parser scripts (C#, PHP, TS, Dart, Unity, C++)
- **Dependencies**: langgraph, langchain-core, langchain-openai, langchain-anthropic, tree-sitter, click, pyyaml, tiktoken, mcp
- **Entry points**: `ctx-build` CLI command, MCP server (`src.mcp_server`)

### 2. ARCHITECTURE

**Type**: Modular Monolith with Plugin Architecture for parsers

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI (src/cli.py)                      │
│                    MCP Server (src/mcp_server.py)            │
├─────────────────────────────────────────────────────────────┤
│                     Agent (src/agent.py)                     │
│              LangGraph StateGraph (agent ↔ tools)            │
├─────────────────────────────────────────────────────────────┤
│    Tools (src/tools.py)    │   Prompts (src/prompts/)        │
│    14 MCP-style tools      │   SYSTEM_PROMPT                 │
├─────────────────────────────────────────────────────────────┤
│              Index (src/index.py)                            │
│   ProjectIndex, DependencyGraph, SQLite cache                │
├──────────────────┬──────────────────────────────────────────┤
│  Scanner          │  Parsers (src/parsers/)                  │
│  (src/scanner.py) │  base.py → registry.py → csharp.py      │
│  FileEntry,       │                php.py, typescript.py     │
│  RepoIndex,       │                dart.py, cpp.py, unity.py │
│  FolderNode       │  External: Roslyn, PHP, TS, Dart         │
└──────────────────┴──────────────────────────────────────────┘
```

**Layers**:
1. **CLI/MCP Layer** (`cli.py`, `mcp_server.py`) — entry points, argument parsing, model creation
2. **Agent Layer** (`agent.py`) — LangGraph StateGraph with agent+tool nodes, routes tool calls
3. **Tool Layer** (`tools.py`) — 14 tools bound to ProjectIndex, exposed to LLM
4. **Index Layer** (`index.py`) — ProjectIndex (repo+ast+deps), SQLite cache, PageRank ranking, entity classification
5. **Scanner Layer** (`scanner.py`) — walks filesystem, classifies files by type/language, builds tree
6. **Parser Layer** (`parsers/`) — Plugin architecture: BaseParser ABC → 6 language-specific parsers, each with primary (external tool) and fallback (regex) modes
7. **Config Layer** (`config.py`) — YAML config loading, project type detection via markers

### 3. RELATED FILES

| File | Purpose | Relevance |
|------|---------|-----------|
| `src/cli.py` | CLI entry point with Click commands | Entry point, model creation, orchestrates build |
| `src/agent.py` | LangGraph agent with tool routing | Core agent loop, StateGraph, tool dispatch |
| `src/tools.py` | 14 MCP-style tools for codebase analysis | All tools the agent uses (list_files, read_file, etc.) |
| `src/index.py` | ProjectIndex, DependencyGraph, SQLite cache | Central data layer: build, load, rank, classify |
| `src/scanner.py` | Filesystem scanner, file classification | FileEntry, RepoIndex, exclusion patterns |
| `src/config.py` | Config loading, project type detection | .ai-context.yml parsing, DEFAULT_EXCLUDE |
| `src/parsers/base.py` | AST dataclasses (ClassDecl, MethodDecl, etc.) | Shared data model for all parsers |
| `src/parsers/registry.py` | Parser registry (factory pattern) | Maps parser_id → parser class |
| `src/parsers/csharp.py` | C# parser (Roslyn external + regex fallback) | C#/ASP.NET parsing |
| `src/parsers/typescript.py` | TypeScript parser (Node external + regex fallback) | TS/Vue parsing |
| `src/parsers/php.py` | PHP parser (PHP external + regex fallback) | Laravel/PHP parsing |
| `src/parsers/dart.py` | Dart parser (Dart external + regex fallback) | Flutter parsing |
| `src/parsers/cpp.py` | C++ parser (tree-sitter + regex fallback) | Unreal Engine parsing |
| `src/parsers/unity.py` | Unity parser (wraps CSharpParser + meta parsing) | Unity-specific parsing |
| `src/prompts/system.py` | SYSTEM_PROMPT for the agent | Defines agent behavior and output format |
| `src/mcp_server.py` | MCP server exposing tools to Claude Code | Alternative entry point via MCP protocol |
| `src/gitlab.py` | GitLab API client for MR context | GitLab integration |
| `.ai-context.yml` | Project configuration file | Configures indexing, model, context limits |

### 4. DEPENDENCY GRAPH

**Module-level dependencies** (src/ directory):

```
cli.py → agent.py, config.py, index.py, tools.py
mcp_server.py → config.py, index.py, tools.py, agent.py
agent.py → prompts/system.py
tools.py → index.py
index.py → config.py, scanner.py, parsers/base.py, parsers/registry.py
scanner.py → config.py
parsers/registry.py → parsers/base.py, parsers/csharp.py, parsers/php.py, parsers/typescript.py, parsers/dart.py, parsers/unity.py, parsers/cpp.py
parsers/csharp.py → parsers/base.py
parsers/php.py → parsers/base.py
parsers/typescript.py → parsers/base.py
parsers/dart.py → parsers/base.py
parsers/cpp.py → parsers/base.py
parsers/unity.py → parsers/base.py, parsers/csharp.py
config.py → (no internal deps)
scanner.py → config.py
gitlab.py → (no internal deps)
```

**Key dependency chains**:
- `cli.py` → `config.py` → (standalone)
- `cli.py` → `index.py` → `scanner.py` → `config.py`
- `index.py` → `parsers/registry.py` → `parsers/*.py` → `parsers/base.py`
- `tools.py` → `index.py` (tools are closures bound to a ProjectIndex instance)

**Call graph** (agent execution flow):
```
main() → load_config() → ProjectIndex.load_or_build() → RepoScanner.scan()
                                                       → parser.parse() for each language
                                                       → DependencyGraph.from_ast()
       → create_tools(index) → returns 14 tool functions
       → CtxBuilderAgent(model, tools) → _build_graph() → StateGraph
       → agent.run(task) → graph.invoke() → _agent_node() → LLM with tools
                                            → _router() → "tools" or "end"
                                            → _tool_node() → dispatch to tool by name
```

### 5. CONVENTIONS

**Naming Conventions** (from source code analysis):

1. **Classes**: PascalCase — `CtxBuilderAgent`, `ProjectIndex`, `DependencyGraph`, `RepoScanner`, `FileEntry`, `FolderNode`, `CSharpParser`, `PHPParser`
2. **Functions/Methods**: snake_case — `load_config`, `create_tools`, `_build_graph`, `_agent_node`, `_router`, `_classify_file`, `_is_excluded`
3. **Constants**: UPPER_SNAKE_CASE — `SYSTEM_PROMPT`, `DEFAULT_EXCLUDE`, `DEFAULT_CONFIG`, `PROJECT_MARKERS`, `TEST_PATTERNS`, `DOC_EXTENSIONS`, `LANGUAGE_MAP`, `ENTITY_PRIORITY`
4. **Private methods**: `_` prefix — `_build_graph`, `_agent_node`, `_tool_node`, `_router`, `_is_excluded`, `_classify_file`, `_add_to_tree`, `_page_rank`, `_guess_entity_type`, `_classify_single_entity`
5. **Abstract methods**: `@abstractmethod` — `check_available()`, `parse()` in `BaseParser`
6. **Dataclasses**: `@dataclass` with `field(default_factory=...)` — `FileEntry`, `FolderNode`, `RepoIndex`, `Config`, `ProjectType`, `ClassDecl`, `MethodDecl`, `Parameter`, `FileAST`, `ASTIndex`, `DependencyGraph`, `FileInfo`, `ProjectIndex`
7. **Type aliases**: `AgentState(TypedDict)` — single TypedDict for LangGraph state
8. **Parser classes**: `{Language}Parser` suffix — `CSharpParser`, `PHPParser`, `TypeScriptParser`, `DartParser`, `CppParser`, `UnityParser`
9. **Registry pattern**: `PARSER_REGISTRY: dict[str, type[BaseParser]]` — maps string IDs to parser classes
10. **Tool functions**: lowercase snake_case — `list_files`, `read_file`, `search_symbol`, `get_dependencies`, `find_files`, `get_call_graph`, `get_module_graph`, `sample_signatures`, `rank_files`, `find_similar`, `compact_file`, `classify_entities`, `get_summary`, `get_docs`

**Architectural Patterns**:
- **Plugin Architecture**: Parser registry with `BaseParser` ABC, each parser self-registers via `PARSER_REGISTRY`
- **Strategy Pattern**: Each parser has primary (external tool) and fallback (regex) strategies
- **Factory Pattern**: `get_parser(parser_id)` creates parser instances; `create_model(provider, model)` creates LLM instances
- **Repository Pattern**: `ProjectIndex` acts as a repository for file/class/dependency data
- **Agent Pattern**: LangGraph `StateGraph` with agent+tool nodes, conditional routing
- **Dependency Injection**: Tools are closures created by `create_tools(index)` — bound to a `ProjectIndex` instance
- **Caching**: SQLite-based index cache with incremental updates

**Style Conventions**:
- **Type hints**: Full type annotations on all functions (`def load_config(...) -> Config`, `def scan(self) -> RepoIndex`)
- **Error handling**: Graceful fallbacks — parser failure → regex fallback → empty ASTIndex with errors
- **Secrets masking**: `mask_secrets()` applied to all file reads before returning to LLM
- **Token awareness**: `count_tokens()` used throughout, large file warnings at 80+ lines / 2000+ tokens
- **Async**: MCP server uses `async def`, CLI agent is synchronous
- **Config merging**: Deep merge of default config with user `.ai-context.yml`

### 6. SIMILAR IMPLEMENTATIONS

| Class | File | Why Similar |
|-------|------|-------------|
| `CSharpParser` | `src/parsers/csharp.py` | Extends `BaseParser`, implements `check_available()` + `parse()`, has fallback regex mode |
| `PHPParser` | `src/parsers/php.py` | Extends `BaseParser`, same pattern: external tool → regex fallback |
| `TypeScriptParser` | `src/parsers/typescript.py` | Extends `BaseParser`, same pattern: external tool → regex fallback |
| `DartParser` | `src/parsers/dart.py` | Extends `BaseParser`, same pattern: external tool → regex fallback |
| `CppParser` | `src/parsers/cpp.py` | Extends `BaseParser`, uses tree-sitter (no external tool), has regex fallback |
| `UnityParser` | `src/parsers/unity.py` | Extends `BaseParser`, wraps `CSharpParser`, adds `.meta` file parsing |
| `DependencyGraph` | `src/index.py` | `@dataclass` with `from_ast()` classmethod, builds from AST data |
| `ProjectIndex` | `src/index.py` | `@dataclass` with `build()` + `load_or_build()` classmethods, central data hub |
| `RepoScanner` | `src/scanner.py` | Single-purpose class with `scan()` + `incremental_scan()` methods |

### 7. TASK CONTEXT

**What ctx-builder is**: A Python tool that analyzes codebases and produces structured context documents for LLMs. It uses a LangGraph agent that has 14 tools to explore a project, then outputs an 8-section document.

**Key systems**:
- **Agent loop** (`src/agent.py`): `CtxBuilderAgent` uses LangGraph `StateGraph` with two nodes — "agent" (LLM call) and "tools" (tool execution). The router checks if the last message has tool_calls → routes to "tools", otherwise "end".
- **Tools** (`src/tools.py`): 14 tools created by `create_tools(index)`. Each tool is a closure bound to a `ProjectIndex`. Tools include: `get_summary`, `get_docs`, `get_module_graph`, `find_files`, `classify_entities`, `sample_signatures`, `get_dependencies`, `get_call_graph`, `search_symbol`, `find_similar`, `rank_files`, `compact_file`, `read_file`, `list_files`.
- **Index** (`src/index.py`): `ProjectIndex` holds `RepoIndex` (file metadata), `ASTIndex` (parsed classes/methods), and `DependencyGraph` (imports, call graph, module graph). Built via `build()` or loaded from SQLite cache via `load_or_build()`.
- **Parsers** (`src/parsers/`): Each parser has a primary mode (external tool like Roslyn, PHP script, Node script, tree-sitter) and a regex fallback. All return `ASTIndex` with `FileAST` → `ClassDecl` → `MethodDecl` hierarchy.
- **Config** (`src/config.py`): Loads `.ai-context.yml`, detects project types by checking for markers (`.csproj`, `composer.json`, `package.json`, `pubspec.yaml`, `Assets/`, `.uproject`).

**Important patterns to follow**:
- All tools are created via `create_tools(index)` — they're closures, not classes
- The agent's system prompt is in `src/prompts/system.py` as `SYSTEM_PROMPT`
- The output format is exactly 8 sections (PROJECT SUMMARY, ARCHITECTURE, RELATED FILES, DEPENDENCY GRAPH, CONVENTIONS, SIMILAR IMPLEMENTATIONS, TASK CONTEXT, RELEVANT CODE SNIPPETS)
- Secrets are masked via `mask_secrets()` before any file content is returned
- Token counting uses `tiktoken` via `count_tokens()`
- The MCP server (`src/mcp_server.py`) exposes the same tools via MCP protocol for Claude Code integration

### 8. RELEVANT CODE SNIPPETS

**Snippet 1** — Agent loop with LangGraph StateGraph (`src/agent.py`, lines 22-37):
```python
def _build_graph(self) -> Any:
    builder = StateGraph(AgentState)
    builder.add_node("agent", self._agent_node)
    builder.add_node("tools", self._tool_node)
    builder.set_entry_point("agent")
    builder.add_conditional_edges(
        "agent",
        self._router,
        {"tools": "tools", "end": END},
    )
    builder.add_edge("tools", "agent")
    return builder.compile()
```
This is the core agent architecture — a two-node cycle where the LLM (agent node) calls tools, and results flow back to the LLM until no more tool calls are needed.

**Snippet 2** — Tool creation as closures (`src/tools.py`, lines 47-51):
```python
def create_tools(index: ProjectIndex) -> list:
    """Create tool instances bound to a ProjectIndex."""
    @tool
    def list_files(directory: str = ".") -> str:
        ...
```
All 14 tools are closures capturing the `index` parameter. This is the dependency injection pattern used throughout.

**Snippet 3** — ProjectIndex build pipeline (`src/index.py`, lines 106-131):
```python
@classmethod
def build(cls, config: Config, force: bool = False) -> ProjectIndex:
    scanner = RepoScanner(config)
    repo = scanner.scan()
    ast = ASTIndex()
    for parser_id in config.parsers_needed:
        parser = get_parser(parser_id)
        if parser is None or not parser.check_available():
            continue
        eligible = [p for p, e in repo.files.items() if e.ast_eligible and e.language == parser.language]
        if not eligible:
            continue
        result = parser.parse(str(config.project_path), eligible)
        ast.files.update(result.files)
    deps = DependencyGraph.from_ast(ast, repo)
    return cls(repo=repo, ast=ast, deps=deps)
```
The full build pipeline: scan → parse each language → build dependency graph.

**Snippet 4** — Parser registry with factory (`src/parsers/registry.py`, lines 23-48):
```python
PARSER_REGISTRY: dict[str, type[BaseParser]] = {
    "csharp": CSharpParser,
    "php": PHPParser,
    "typescript": TypeScriptParser,
    "dart": DartParser,
    "unity": UnityParser,
    "cpp": CppParser,
}

def get_parser(parser_id: str) -> BaseParser | None:
    cls = PARSER_REGISTRY.get(parser_id)
    if cls is None:
        return None
    return cls()
```
Simple plugin registry — maps string IDs to parser classes, creates instances on demand.

**Snippet 5** — Entity classification by name suffix (`src/index.py`, lines 393-429):
```python
# Class name suffixes
if name_lower.endswith("controller"):
    return "controller"
if name_lower.endswith("service"):
    return "service"
if name_lower.endswith("repository") or name_lower.endswith("repo"):
    return "repository"
if name_lower.endswith("dto") or name_lower.endswith("model") or name_lower.endswith("viewmodel"):
    return "dto"
if name_lower.endswith("entity") or name_lower.endswith("domain"):
    return "entity"
```
Entity classification uses a cascade of heuristics: base type signals → class name suffixes → folder path fallback. This is the convention detection engine.