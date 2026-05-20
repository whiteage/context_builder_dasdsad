from typing import TypedDict, Any, Literal, Annotated

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage, AnyMessage
from langgraph.graph import END, StateGraph, add_messages

from src.prompts.system import SYSTEM_PROMPT


class AgentState(TypedDict):
    messages : Annotated[list[AnyMessage],add_messages]



class CtxBuilderAgent:
    def __init__(self, model : BaseChatModel, tools: list) -> None:
        self.llm = model
        self.tools = tools
        self._tools_by_name = {t.name : t for t in self.tools}
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

        return {"messages": results}

    @staticmethod
    def _router(state: AgentState) -> Literal["tools", "end"]:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return "end"

    def run(self, task: str) -> str:
        result = self.graph.invoke({
            "messages": [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=task)]
        })
        # LangGraph may return a final message with tool_calls and content=None.
        # Walk backwards to find the last message with actual text content.
        for msg in reversed(result["messages"]):
            content = getattr(msg, "content", None)
            if content:
                return content
        return "Agent produced no text output — the model may have returned empty content."