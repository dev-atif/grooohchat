# nodes/chat_node.py

from utils.schema_type import ChatState
from utils.model import llm_model
from utils.prompts import (
    INITIAL_GREETING_PROMPT, 
    get_summary_prompt, 
    get_help_prompt, 
    get_rag_prompt
)
from tools.contact_tool import ContactInformationSchema
from langchain_core.messages import ToolMessage

def generate_node(state: ChatState):
    """Generates an answer based on context, history, or chat meta-commands."""
    
    response = None
   
    if not state.messages or len(state.messages) == 0 or not state.question:
        response = llm_model.invoke(INITIAL_GREETING_PROMPT)
        return {"messages": [response]}

    # 1. INTERCEPT: Handle Chat Summarization Requests
    if any(k in state.question.lower() for k in ["summarize", "summary"]):
        history_str = "\n".join([f"{type(m).__name__}: {m.content}" for m in state.messages])
        prompt = get_summary_prompt(history_str)
        response = llm_model.invoke(prompt)

    # 2. INTERCEPT: Handle General Assistance/Polite prompts
    elif not state.context and any(k in state.question.lower() for k in ["help me", "what can you do"]):
        prompt = get_help_prompt(state.question)
        response = llm_model.invoke(prompt)

    # 3. STANDARD CRITICAL RAG PROMPT
    else:
        prompt = get_rag_prompt(state.messages, state.context or "", state.question)
        response = llm_model.invoke(prompt)

    # =====================================================
    # TOOL-SAFE SUBMISSION LOGIC WITH FIELD SCANNING
    # =====================================================

    total_messages = len(state.messages) + 1
    submission_string = "Ready to work on the project?"

    # Check 1: Structural verification (ToolMessage or tool_calls metadata)
    has_tool_msg = any(isinstance(m, ToolMessage) for m in state.messages)
    has_tool_call_history = any(bool(getattr(m, "tool_calls", None)) for m in state.messages)
    is_current_tool_call = bool(getattr(response, "tool_calls", None))

    # Check 2: Dynamic text scanning for schema keys (e.g., 'name', 'email', 'phone')
    schema_fields = set(ContactInformationSchema.model_fields.keys())
    schema_field_found_in_text = any(
        isinstance(m.content, str) and any(field in m.content.lower() for field in schema_fields)
        for m in state.messages
    )

    # Combine all checks into a definitive boolean flag
    # If any tool indicator OR text match is active, tool_involved becomes True
    tool_involved = (
        has_tool_msg 
        or has_tool_call_history 
        or is_current_tool_call 
        or schema_field_found_in_text
    )

    # ONLY append if depth requirement met AND absolutely no tools/fields are involved
    if total_messages >= 4 and not tool_involved:
        if hasattr(response, "content") and response.content:
            if submission_string not in response.content:
                response.content += f"\n\n{submission_string}"
        elif hasattr(response, "content") and not response.content:
            response.content = submission_string

    return {"messages": [response]}