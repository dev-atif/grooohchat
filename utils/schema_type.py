from pydantic import BaseModel, Field
from typing import Optional, Annotated
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ChatState(BaseModel):
    question: str = ""
    # Added Field factory so the state can start with an empty message list safely
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    context: Optional[str] = None