from typing import TypedDict, Any, Literal, Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage, AnyMessage
from langgraph.graph import END, StateGraph, add_messages

from src.prompts.system import make_gatherer_prompt, make_writer_prompt, STRUCTURED_TOOLS


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    step_count: int


class CtxBuilderAgent:
    def __init__(self, model: BaseChatModel, tools: list, ctx=None, max_steps: int = 12) -> None:
        self.llm = model
        self.tools = tools
        self.ctx = ctx
        self.max_steps = max_steps
        self._tools_by_name = {t.name: t for t in self.tools}
        self.graph = self._build_graph()

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
        results: list[ToolMessage] = []

        for tc in last.tool_calls:
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
            results.append(ToolMessage(content=str(content), tool_call_id=tc["id"]))

        new_step = state.get("step_count", 0) + 1
        return {"messages": results, "step_count": new_step}

    def _router(self, state: AgentState) -> Literal["tools", "end"]:
        step = state.get("step_count", 0)
        if step >= self.max_steps:
            return "end"
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return "end"

    def run(self, task: str, token_budget: int = 30000) -> str:
        # Phase 1: Gather — let the agent collect tool data
        gatherer_prompt = make_gatherer_prompt(token_budget=token_budget, max_steps=self.max_steps, task=task)
        result = self.graph.invoke({
            "messages": [SystemMessage(content=gatherer_prompt), HumanMessage(content=task)],
            "step_count": 0,
        })

        # Extract structured tool results from the conversation
        collected = self._extract_tool_results(result["messages"])

        if not collected:
            return "Gatherer collected no data — no tools were called. Check project indexing."

        # Store debug info for caller
        self.last_tools = list(collected.keys())
        self.last_has_code = bool(collected.get("read_file") or collected.get("compact_file"))
        self.last_tool_bytes = {k: len(v) for k, v in collected.items()}

        # Phase 2: Write — produce the document from collected data
        writer_prompt = make_writer_prompt(task=task, collected=collected)
        try:
            response = self.llm.invoke(writer_prompt)
            content = getattr(response, "content", None)
            if not content:
                return "Writer produced no output."
            result_text = str(content)

            # Post-process: strip fabricated snippets if gatherer didn't collect source code
            if not self.last_has_code:
                import re
                result_text = re.sub(
                    r'\n### 8\.\s*RELEVANT CODE SNIPPETS.*$',
                    '\n### 8. RELEVANT CODE SNIPPETS\n'
                    'No code snippets available — gatherer did not call read_file or compact_file.\n'
                    f'Collected tools: {", ".join(self.last_tools)}.',
                    result_text, flags=re.DOTALL
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
