"""System prompts for the ctx-builder agent (gatherer + writer)."""

# Tools the gatherer should prioritize for structured data collection.
# These are the high-ROI tools that give broad coverage without burning tokens.
STRUCTURED_TOOLS = [
    "get_summary", "get_docs", "get_module_graph", "classify_entities",
    "sample_signatures", "search_symbol", "find_files", "rank_files",
    "get_dependencies", "get_call_graph", "find_similar",
    "compact_file", "read_file", "list_files", "get_token_budget",
]


def _parse_unknown_pct(classify_output: str) -> int | None:
    """Parse unknown percentage from classify_entities output."""
    import re
    total_match = re.search(r"\((\d+)\s+files\)", classify_output)
    unknown_match = re.search(r"unknown:\s*(\d+)\s+files", classify_output)
    if total_match and unknown_match:
        total = int(total_match.group(1))
        unknown = int(unknown_match.group(1))
        if total > 0:
            return round(unknown * 100 / total)
    return None


def make_gatherer_prompt(token_budget: int = 30000, max_steps: int = 12, task: str = "") -> str:
    is_code_gen = any(kw in task.lower() for kw in [
        "code generation", "add a new", "create a new", "implement",
        "add new", "create new",
    ])

    extra_rule = ""
    if is_code_gen:
        extra_rule = """
## Code Generation — CRITICAL
- find_files to locate the EXACT file that does what you're asked to create.
- read_file on that file (FULL, 80-120 lines) — NOT compact_file. You need the complete implementation to understand the pattern.
- Then compact_file on 1-2 related files for additional context.
"""

    return f"""You are a data-collection agent. Your ONLY job: call tools to gather information about a codebase.

## Required tool calls (in order)
1. get_summary — always first
2. get_docs — always second
3. classify_entities — always
4. search_symbol — extract 2-4 key terms from the task, search each
5. get_dependencies — for EVERY file found by search_symbol (at least 2 files)
6. sample_signatures — always
7. compact_file — top-3 relevant files found above
8. find_similar — on the main class from the task
9. get_module_graph — for architecture/refactoring tasks
10. read_file — on the PRIMARY target file for the task, 80-120 lines{extra_rule}

## Key rules
- You do NOT analyze, summarize, or write a document — a separate writer agent will handle that.
- get_dependencies is MANDATORY. Call it for at least 2 files found via search_symbol.
- Never re-read file ranges already covered (check get_token_budget before reads).
- For Code Generation: read_file on the target file FIRST, then compact_file on related files.
- For Bug Fixing / Architecture: compact_file first, then read_file on critical sections.
- Do NOT stop before completing all required steps (1-7 minimum). Only stop when get_dependencies AND compact_file have been called.

## Limits
- {token_budget} tokens budget for tool outputs.
- {max_steps} max tool-calling iterations.
"""


def make_writer_prompt(task: str, collected: dict[str, str]) -> str:
    has_source_code = bool(collected.get("read_file") or collected.get("compact_file"))
    collected_tools = list(collected.keys())

    # Extract unknown% from classify_entities
    unknown_pct = _parse_unknown_pct(collected.get("classify_entities", ""))

    arch_section = "### 2. ARCHITECTURE — pattern (MVC, DDD, Clean, ECS, Layered, Modular Monolith...), layers, responsibilities"
    conv_section = "### 5. CONVENTIONS — naming rules with examples, patterns, style. Under 50 lines."

    if unknown_pct is not None and unknown_pct > 50:
        arch_section += (
            f"\\n**Code quality note:** {unknown_pct}% of source files have no recognizable entity type "
            "(no base classes, interfaces, or naming conventions). "
            "Do NOT invent a clean architecture — describe what you ACTUALLY see in the data. "
            "If there's no discernible pattern, write: \"No consistent architecture detected — "
            f"{unknown_pct}% of files have unclassified entity types.\""
        )
        conv_section += (
            f"\\n**Code quality note:** {unknown_pct}% unknown entities — naming is likely inconsistent. "
            "Report only conventions you can VERIFY from sample_signatures. "
            "If patterns are inconsistent, say so explicitly."
        )

    sections = [
        "### 1. PROJECT SUMMARY — tech stack, file count, languages, project type (2-4 sentences)",
        arch_section,
        "### 3. RELATED FILES — at least 5 files with path, entity type, purpose, relevance to task",
        "### 4. DEPENDENCY GRAPH — use get_dependencies tool output. List actual imports/imported-by counts per file. If no get_dependencies data: write \"No dependency data collected — gatherer did not call get_dependencies.\" Do NOT invent dependency chains from general knowledge.",
        conv_section,
        "### 6. SIMILAR IMPLEMENTATIONS — at least 3 classes with same patterns, with file paths",
        "### 7. TASK CONTEXT — self-contained summary for downstream AI: what to touch, follow, avoid",
    ]

    if has_source_code:
        sections.append(
            "### 8. RELEVANT CODE SNIPPETS — 3-5 snippets (3-10 lines each) with file path, line numbers, "
            "relevance. Copy code VERBATIM from read_file tool output (NOT compact_file). "
            "read_file contains real code with line numbers — use it directly, do not paraphrase. "
            "Only use compact_file if read_file is unavailable for that specific file. "
            "Do NOT modify, rewrite, or invent code."
        )
        section_count = "8"
        budget_line = "Budget: ~15% summary, ~20% architecture, ~15% files, ~15% deps, ~15% conventions, ~5% similar, ~10% task context, ~5% snippets."
    else:
        # Do NOT mention section 8 at all — writer will fabricate if given the opportunity
        section_count = "7"
        budget_line = "Budget: ~20% summary, ~25% architecture, ~15% files, ~15% deps, ~15% conventions, ~5% similar, ~5% task context."

    parts = [f"""You are a context-document writer. Produce a {section_count}-section AI-ready context document based ONLY on the collected data below.

**Task:** {task}
**Tools used:** {', '.join(collected_tools)}
**Has source code (read_file/compact_file):** {'YES — use it for section 8' if has_source_code else 'NO — section 8 is NOT required'}

## CRITICAL RULES
- Use ONLY data from the collected tools below. Do NOT use your own knowledge of frameworks, languages, or patterns.
- If a tool's output is missing, say so. Never fill gaps from general knowledge.
- Do NOT fabricate, invent, or reconstruct code snippets, file paths, line numbers, or class names.

## Output format (ALL {section_count} sections required)

{chr(10).join(sections)}

{budget_line}
Shrink sections if low on space — never skip a section.
No ASCII box diagrams. Max 3 examples per pattern. Each fact once.

## Collected data

"""]
    for tool_name, tool_output in collected.items():
        # Trim overly long tool outputs to prevent context overflow
        trimmed = tool_output
        if len(tool_output) > 12000:
            trimmed = tool_output[:12000] + f"\n... (trimmed, total {len(tool_output)} chars)"
        parts.append(f"### {tool_name}\n```\n{trimmed}\n```\n")
    return "\n".join(parts)
