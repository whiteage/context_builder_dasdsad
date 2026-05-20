---
name: ctx-build
description: Build AI-ready context from any project for code review, generation, refactoring, bug fixing, or documentation.
model: claude-opus-4-7
---

# ctx-build — Context Builder for Claude Code

Invoke this skill when the user asks to:
- "analyze the architecture of ..."
- "review this project"
- "find how X works in the codebase"
- "what are the conventions in this project"
- "what files would be impacted by changing X"
- "collect context for code review / refactoring / bug fixing"

## Usage

Run ctx-build via the MCP tools `ctx_summary` (fast, no LLM) or `ctx_build` (full AI analysis).

### Quick summary (no LLM cost)
```
ctx_summary with project="<path>"
```

### Full context (with LLM)
```
ctx_build with:
  project="<path>"
  task="Code Review: ..."
  provider="deepseek" (or "openai", "anthropic")
  model="deepseek-chat" (or "gpt-4o", "claude-opus-4-7")
```

### Search for symbols
```
ctx_search with project="<path>" symbol="<class_or_method_name>"
```

### Get file dependencies
```
ctx_dependencies with project="<path>" file="<relative_path>"
```

### Classify entities
```
ctx_entities with project="<path>"
```

## Available MCP Tools

1. **ctx_build** — Full AI context document (8 sections: PROJECT SUMMARY, ARCHITECTURE, RELATED FILES, DEPENDENCY GRAPH, CONVENTIONS, SIMILAR IMPLEMENTATIONS, TASK CONTEXT, RELEVANT CODE SNIPPETS)
2. **ctx_summary** — Instant project overview (files, languages, structure tree)
3. **ctx_search** — Find classes/methods by name
4. **ctx_dependencies** — What imports a file, what it imports
5. **ctx_entities** — Classify files by type (controller, service, etc.)

## Tips
- Always start with `ctx_summary` to understand project scale
- Use `ctx_build` when you need deep architecture analysis
- The context output is token-optimized (~5000 tokens average)
- Works with: ASP.NET Core, Laravel, Node.js, Vue.js, Flutter, Unity, Unreal Engine, Rust (basic)
