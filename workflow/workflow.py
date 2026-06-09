from langgraph.graph import END, START, StateGraph
from utils.schema_type import ChatState
from nodes.chat_node import generate_node
from nodes.retriever_node import retriever_node
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode,tools_condition
from tools.tools_list import tools
def _retrieve_node(state: ChatState, *, config=None, store=None):
    return retriever_node(state)


def _generate_node(state: ChatState, *, config=None, store=None):
    return generate_node(state)

tool_node=ToolNode(tools)
workflow = StateGraph(ChatState)
workflow.add_node("retrieve", _retrieve_node)
workflow.add_node("generate", _generate_node)
workflow.add_node("tools", tool_node)
workflow.add_edge(START,"retrieve")
workflow.add_edge("retrieve","generate")
workflow.add_conditional_edges("generate",tools_condition)
workflow.add_edge("tools","generate")


memory = MemorySaver()
app = workflow.compile(checkpointer=memory)