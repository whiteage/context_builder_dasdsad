import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TypedDict, Any, Literal, Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage, AnyMessage
from langgraph.graph import END, StateGraph, add_messages

from src.prompts.system import make_gatherer_prompt, make_writer_prompt, make_planner_prompt, STRUCTURED_TOOLS

# Tools that are always needed and independent of the task — first batch
_PRE_TOOLS = ["get_summary", "get_docs", "classify_entities", "get_module_graph"]

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    step_count: int


class CtxBuilderAgent:
    def __init__(self, model: BaseChatModel, tools: list, ctx=None) -> None:
        self.llm = model
        self.tools = tools
        self.ctx = ctx
        self._tools_by_name = {t.name: t for t in self.tools}
        self.graph = self._build_graph()

    def _extract_keywords(self, task: str) -> list[str]:
        """Use LLM to extract searchable keywords from the task.

        One lightweight LLM call — no hardcoded patterns or word lists.
        Falls back to regex word extraction if LLM fails.
        """
        import json as _json

        prompt = (
            "Extract up to 8 search keywords from this task description. "
            "Return ONLY a JSON array of lowercase strings. "
            "Focus on technical terms, framework names, patterns, and concepts "
            "relevant for searching a codebase. Exclude generic verbs and filler words.\n"
            "Examples:\n"
            '- "fix memory leak in connection pool" → ["memory", "leak", "connection", "pool", "dispose", "close"]\n'
            '- "add rate limiting to REST API endpoints" → ["rate", "limit", "throttle", "endpoint", "middleware", "guard"]\n'
            f"Task: {task}\n"
            "JSON:"
        )

        try:
            response = self.llm.invoke(prompt)
            raw = str(getattr(response, "content", "[]")).strip()
            # Strip markdown fences if present
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0]
            keywords = _json.loads(raw)
            if isinstance(keywords, list):
                return [str(k).lower() for k in keywords if str(k).strip()][:8]
        except Exception:
            pass

        # Fallback: extract all words >= 3 chars, take first 5 unique
        words = re.findall(r"[a-zA-Z]{3,}", task.lower())
        seen: set[str] = set()
        result: list[str] = []
        for w in words:
            if w not in seen:
                seen.add(w)
                result.append(w)
        return result[:5]

    def _invoke_tool(self, name: str, args: dict | None = None) -> str:
        """Call a tool by name, returning its string output."""
        fn = self._tools_by_name.get(name)
        if not fn:
            return f"Unknown tool: {name}"
        try:
            content = fn.invoke(args or {})
            if content is None:
                return f"Tool '{name}' returned empty result."
            return str(content)
        except Exception as e:
            return f"Tool '{name}' error: {str(e)}"

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

    def _agent_node(self, state: AgentState) -> dict[str, list[Any]]:
        llm_with_tools = self.llm.bind_tools(self.tools)
        response = llm_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def _tool_node(self, state: AgentState) -> dict[str, list[Any]]:
        last = state["messages"][-1]
        tool_calls = last.tool_calls

        def _invoke_one(tc):
            fn = self._tools_by_name.get(tc["name"])
            if fn:
                try:
                    content = fn.invoke(tc["args"])
                    if content is None:
                        content = f"Tool '{tc['name']}' returned empty result."
                except Exception as e:
                    content = f"Tool '{tc['name']}' error: {str(e)}"
            else:
                content = f"Unknown tool: {tc['name']}"
            return ToolMessage(content=str(content), tool_call_id=tc["id"])

        if len(tool_calls) <= 1:
            results = [_invoke_one(tc) for tc in tool_calls]
        else:
            from concurrent.futures import ThreadPoolExecutor, as_completed
            with ThreadPoolExecutor(max_workers=len(tool_calls)) as pool:
                futures = {pool.submit(_invoke_one, tc): tc["id"] for tc in tool_calls}
                # Collect in original order (ToolMessage has tool_call_id for matching)
                results = [f.result() for f in as_completed(futures)]

        new_step = state.get("step_count", 0) + 1
        return {"messages": results, "step_count": new_step}

    def _router(self, state: AgentState) -> Literal["tools", "end"]:
        step = state.get("step_count", 0)
        if step >= 30:
            return "end"
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return "end"

    def _parse_plan(self, raw: str, pre_collected: dict[str, str]) -> dict[str, list[Any]]:
        """Parse LLM planner JSON output into a list of (tool_name, args) per tool."""
        import json as _json
        plan: dict[str, list[Any]] = {}

        # Extract JSON from response (may be wrapped in markdown)
        json_str = raw.strip()
        if "```json" in json_str:
            json_str = json_str.split("```json")[1].split("```")[0]
        elif "```" in json_str:
            json_str = json_str.split("```")[1].split("```")[0]

        try:
            parsed = _json.loads(json_str)
        except _json.JSONDecodeError:
            # Fallback: extract JSON object with regex
            m = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
            if m:
                try:
                    parsed = _json.loads(m.group(0))
                except _json.JSONDecodeError:
                    parsed = {}

        # Ensure mandatory tools
        if not parsed.get("sample_signatures"):
            parsed["sample_signatures"] = True

        # Extract files mentioned in search_symbol results (for get_dependencies fallback)
        search_files: dict[str, int] = {}  # path -> frequency
        for name, output in pre_collected.items():
            if name.startswith("search_symbol:"):
                for line in output.split("\n"):
                    m = re.search(r"in\s+(\S+)", line)
                    if m:
                        path = m.group(1).rstrip(".")
                        if path not in search_files:
                            search_files[path] = 0
                        search_files[path] += 1
        ranked = sorted(search_files, key=lambda p: -search_files[p])

        if not parsed.get("get_dependencies"):
            parsed["get_dependencies"] = ranked[:3]
        else:
            # Always merge planner's choices with top search_symbol files.
            # Planner may pick files that appear in search results but have
            # empty dependency data (e.g. auth middleware), so we add a safety
            # net of the highest-frequency files from search_symbol.
            chosen = parsed["get_dependencies"]
            for f in ranked:
                if f not in chosen and len(chosen) < 5:
                    chosen.append(f)
            parsed["get_dependencies"] = chosen

        plan["sample_signatures"] = [{}] if parsed.get("sample_signatures") else []
        plan["get_dependencies"] = [{"path": p} for p in parsed.get("get_dependencies", [])[:10]]
        plan["compact_file"] = [{"path": p} for p in parsed.get("compact_file", [])[:5]]
        plan["read_file"] = [
            {"path": r["path"], "start_line": r.get("start", 1), "end_line": r.get("end", 0)}
            for r in parsed.get("read_file", [])[:5]
        ]
        plan["find_similar"] = [{"class_name": c} for c in parsed.get("find_similar", [])[:3]]
        plan["find_files"] = [
            {"pattern": f.get("pattern", "*"), "language": f.get("language", ""), "file_type": f.get("file_type", "")}
            for f in parsed.get("find_files", [])[:3]
        ]
        plan["search_symbol"] = [{"name": s} for s in parsed.get("search_symbol", [])[:6]]
        return plan

    def run(self, task: str, token_budget: int = 30000) -> str:
        # Phase 0: Pre-collect always-needed independent tools
        pre_collected: dict[str, str] = {}
        pre_tool_names = list(_PRE_TOOLS)
        # LLM keywords + regex fallback union: guards against LLM variance
        keywords = self._extract_keywords(task)
        regex_words = re.findall(r"[a-zA-Z]{4,}", task.lower())
        seen: set[str] = {k.lower() for k in keywords}
        for w in regex_words:
            if w not in seen:
                seen.add(w)
                keywords.append(w)
        for kw in keywords[:10]:
            pre_tool_names.append(f"search_symbol:{kw}")

        with ThreadPoolExecutor(max_workers=len(pre_tool_names)) as pool:
            futures: dict[str, Any] = {}
            for name in pre_tool_names:
                if name.startswith("search_symbol:"):
                    kw = name.split(":", 1)[1]
                    futures[name] = pool.submit(self._invoke_tool, "search_symbol", {"name": kw})
                else:
                    futures[name] = pool.submit(self._invoke_tool, name)
            for name, fut in futures.items():
                pre_collected[name] = fut.result()

        # Build pre-collected context for planner
        pre_context = "PRE-COLLECTED DATA:\n\n"
        for name, output in pre_collected.items():
            label = name.replace(":", " ") if ":" in name else name
            trimmed = output if len(output) <= 3000 else output[:3000] + f"\n... (trimmed, {len(output)} chars)"
            pre_context += f"### {label}\n```\n{trimmed}\n```\n"

        # Track pre-collected tokens
        from src.index import count_tokens
        pre_tokens = count_tokens(pre_context)
        if self.ctx:
            self.ctx.consume(pre_tokens)
        adjusted_budget = token_budget - pre_tokens

        # Phase 1: Planner — LLM returns JSON plan (1 LLM call instead of 5-25)
        planner_prompt = make_planner_prompt(task=task, token_budget=adjusted_budget)
        plan_raw = ""
        try:
            response = self.llm.invoke(planner_prompt + "\n\n" + pre_context)
            plan_raw = str(getattr(response, "content", ""))
        except Exception as e:
            plan_raw = "{}"

        plan = self._parse_plan(plan_raw, pre_collected)

        # Phase 2: Execute all planned tools in parallel
        planned_results: dict[str, list[str]] = {}
        all_calls: list[tuple[str, str, dict]] = []  # (key, tool_name, args)
        for tool_name in ("sample_signatures", "get_dependencies", "compact_file",
                          "read_file", "find_similar", "find_files", "search_symbol"):
            for args in plan.get(tool_name, []):
                all_calls.append((tool_name, tool_name, args))

        if all_calls:
            with ThreadPoolExecutor(max_workers=len(all_calls)) as pool:
                fut_to_key: dict[Any, str] = {}
                for key, tool_name, args in all_calls:
                    fut = pool.submit(self._invoke_tool, tool_name, args)
                    fut_to_key[fut] = tool_name
                for fut in as_completed(fut_to_key):
                    tool_name = fut_to_key[fut]
                    planned_results.setdefault(tool_name, []).append(fut.result())

        # Merge pre-collected + planned results
        collected: dict[str, str] = {}
        for name, output in pre_collected.items():
            clean_name = name.split(":", 1)[0]  # search_symbol:kw → search_symbol
            if clean_name in collected:
                collected[clean_name] += "\n---\n" + output
            else:
                collected[clean_name] = output
        for name, outputs in planned_results.items():
            joined = "\n---\n".join(outputs)
            if name in collected:
                collected[name] += "\n---\n" + joined
            else:
                collected[name] = joined

        if not collected:
            return "No data collected — check project indexing."

        # Store debug info
        self.last_steps = 1  # 1 planner call
        all_tool_names = list(pre_collected.keys()) + list(planned_results.keys())
        self.last_tools = [n.split(":", 1)[0] for n in all_tool_names]
        self.last_has_code = bool(collected.get("read_file") or collected.get("compact_file"))
        self.last_tool_bytes = {k: len(v) for k, v in collected.items()}

        # Phase 3: Write
        writer_prompt = make_writer_prompt(task=task, collected=collected)
        try:
            response = self.llm.invoke(writer_prompt)
            content = getattr(response, "content", None)
            if not content:
                return "Writer produced no output."
            result_text = str(content)

            if not self.last_has_code:
                import re as _re
                result_text = _re.sub(
                    r'\n### 8\.\s*RELEVANT CODE SNIPPETS.*$',
                    '\n### 8. RELEVANT CODE SNIPPETS\n'
                    'No code snippets available — planner did not include read_file or compact_file.\n'
                    f'Collected tools: {", ".join(self.last_tools)}.',
                    result_text, flags=_re.DOTALL
                )

            return result_text
        except Exception as e:
            return f"Writer error: {str(e)}"

    def _extract_tool_results(self, messages: list) -> dict[str, str]:
        """Pull tool call names and their results out of the conversation history."""
        collected: dict[str, list[str]] = {}
        for msg in messages:
            if isinstance(msg, ToolMessage):
                tool_name = getattr(msg, "tool_call_id", None) or getattr(msg, "name", None)
                # Match tool_call_id back to the preceding AI message's tool_calls
                if tool_name:
                    for prev in messages:
                        tc_list = getattr(prev, "tool_calls", None) or []
                        for tc in tc_list:
                            if tc.get("id") == tool_name:
                                tool_name = tc.get("name", tool_name)
                                break
                collected.setdefault(str(tool_name), []).append(str(msg.content))
        # Deduplicate: keep last occurrence per tool (most complete data)
        result = {}
        for name, contents in collected.items():
            # For most tools, keep the last result (most complete)
            # For read_file, compact_file — keep all since each is a different file
            if name in ("read_file", "compact_file", "get_dependencies"):
                result[name] = "\n---\n".join(contents[-3:])  # Keep last 3 to avoid bloat
            else:
                result[name] = contents[-1] if contents else ""
        return result
