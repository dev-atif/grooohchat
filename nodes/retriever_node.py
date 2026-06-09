from utils.schema_type import ChatState
from utils.retriever import retriever
def retriever_node(State:ChatState):
    docs_retrieved=retriever.invoke(State.question)
    context_retrieved="/n".join([d.page_content for d in docs_retrieved])
    return {"context":context_retrieved}