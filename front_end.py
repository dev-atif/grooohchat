import os
import json
import uuid
import base64
import streamlit as st
from dotenv import load_dotenv

# LangChain Core Object Imports
from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage

# Latest LangGraph Native Control Component
from langgraph.types import Command  

# Project Module Structs
from utils.schema_type import ChatState
from workflow.workflow import app

load_dotenv()

# =====================================================
# STREAMLIT CONFIGURATION
# =====================================================
st.set_page_config(
    page_title="Groooh AI",
    page_icon="⚡",
    layout="centered",
)

def load_external_css(css_file_path):
    if os.path.exists(css_file_path):
        with open(css_file_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_external_css("style.css")

# =====================================================
# CACHE & STATE STORAGE PERSISTENCE
# =====================================================
CACHE_DIR = "chat_caches"
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_path(thread_id):
    return os.path.join(CACHE_DIR, f"cache_{thread_id}.json")

def save_history_to_disk(thread_id, messages):
    serialized = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            serialized.append({"type": "human", "content": msg.content})
        elif isinstance(msg, (AIMessage, AIMessageChunk)):
            serialized.append({"type": "ai", "content": msg.content})

    with open(get_cache_path(thread_id), "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)

def load_history_from_disk(thread_id):
    path = get_cache_path(thread_id)
    if not os.path.exists(path):
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        messages = []
        for msg in data:
            if msg["type"] == "human":
                messages.append(HumanMessage(content=msg["content"]))
            elif msg["type"] == "ai":
                messages.append(AIMessage(content=msg["content"]))
        return messages
    except Exception:
        return []

# =====================================================
# MULTI-THREADING SESSION ROUTING
# =====================================================
if "thread_id" not in st.session_state:
    if "tid" in st.query_params:
        st.session_state.thread_id = st.query_params["tid"]
    else:
        new_id = str(uuid.uuid4())[:8]
        st.session_state.thread_id = new_id
        st.query_params["tid"] = new_id

config = {"configurable": {"thread_id": st.session_state.thread_id}}

if "processing" not in st.session_state:
    st.session_state.processing = False

# =====================================================
# STATE SNAPSHOT & ACTIVE INTERRUPT CHECK
# =====================================================
state_snapshot = app.get_state(config)

# Dynamically discover any pending workflow human review blocks
active_interrupts = (
    state_snapshot.tasks[0].interrupts if state_snapshot.tasks else []
)

if state_snapshot and state_snapshot.values:
    history = (
        state_snapshot.values.get("messages", [])
        if isinstance(state_snapshot.values, dict)
        else getattr(state_snapshot.values, "messages", [])
    )
else:
    history = []

if not history:
    disk_history = load_history_from_disk(st.session_state.thread_id)
    if disk_history:
        history = disk_history
        app.update_state(config, {"messages": history})

# =====================================================
# ENGINE BOOTSTRAP INITIALIZATION
# =====================================================
if not history:
    init_state = ChatState(question="", messages=[])

    with st.spinner("Initializing Workspace Engine..."):
        app.invoke(init_state, config=config)

    snapshot = app.get_state(config)
    history = snapshot.values.get("messages", []) if snapshot and snapshot.values else []

    save_history_to_disk(st.session_state.thread_id, history)
    st.rerun()

# =====================================================
# UI HEADER BRANDING
# =====================================================
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    return ""

img_base64 = get_base64_image("logo.png")

if img_base64:
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:10px;">
            <img src="data:image/png;base64,{img_base64}" style="width:90px;">
            <h2 style="margin:0;">Assistant</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.title("⚡ Assistant")

st.markdown("Ask anything.")

# =====================================================
# CHAT LOG WINDOW RENDERING
# =====================================================
for msg in history:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user", avatar="user.png"):
            st.markdown(msg.content)

    elif isinstance(msg, (AIMessage, AIMessageChunk)):
        if msg.content:
            with st.chat_message("assistant", avatar="logofavicon.png"):
                st.markdown(f'<div class="assistant-red-box">{msg.content}</div>', unsafe_allow_html=True)

# LIVE INTERRUPT RENDERING WITH FULL MARKDOWN SUPPORT
if active_interrupts:
    interrupt_info = active_interrupts[0].value
    
    if isinstance(interrupt_info, dict):
        interrupt_msg = interrupt_info.get("message", str(interrupt_info))
    else:
        interrupt_msg = str(interrupt_info)

    with st.chat_message("assistant", avatar="logofavicon.png"):
        st.markdown(
            f'<div class="assistant-red-box">⚠️ {interrupt_msg}</div>', 
            unsafe_allow_html=True
        )

# =====================================================
# STREAMING & LATEST COMMAND RESUME INTERFACE
# =====================================================
def stream_response(config, user_input=None, is_resume=False):
    box = None
    full_text = ""
    
    if is_resume:
        # Latest LangGraph API: Pass Command(resume=...) directly to the streaming input argument
        stream_kwargs = {
            "input": Command(resume=user_input.strip()), 
            "config": config, 
            "stream_mode": "messages"
        }
    else:
        state_input = ChatState(
            question=user_input,
            messages=[HumanMessage(content=user_input)],
        )
        stream_kwargs = {
            "input": state_input, 
            "config": config, 
            "stream_mode": "messages"
        }

    for msg, metadata in app.stream(**stream_kwargs):
        if isinstance(msg, ToolMessage):
            continue

        if isinstance(msg, (AIMessage, AIMessageChunk)) and msg.content:
            full_text += msg.content

            if box is None:
                box = st.chat_message("assistant", avatar="logofavicon.png").empty()

            box.markdown(
                f'<div class="assistant-red-box">{full_text}</div>',
                unsafe_allow_html=True,
            )

    return full_text

# =====================================================
# ACTION CAPTURE ENTRYPOINT
# =====================================================
def disable_input():
    st.session_state.processing = True

input_placeholder = "Reply yes or no..." if active_interrupts else "Ask anything"

user_input = st.chat_input(
    input_placeholder,
    disabled=st.session_state.processing,
    on_submit=disable_input,
)

if st.session_state.processing and user_input:

    # Output User Bubble immediately
    with st.chat_message("user", avatar="user.png"):
        st.markdown(user_input)

    with st.spinner("Processing..."):
        if active_interrupts:
            # Wake the execution layer up via Command token integration
            result = stream_response(config=config, user_input=user_input, is_resume=True)
            
            # Post-execution graph synchronization
            post_resume_snapshot = app.get_state(config)
            current_values = post_resume_snapshot.values if post_resume_snapshot else {}
            current_messages = (
                current_values.get("messages", []) 
                if isinstance(current_values, dict) 
                else getattr(current_values, "messages", [])
            )
            
            # Form UI feedback patch: Inject an AIMessage if the graph processed changes invisibly
            if current_messages and not isinstance(current_messages[-1], AIMessage):
                last_msg = current_messages[-1]
                
                if isinstance(last_msg, ToolMessage):
                    try:
                        tool_output = json.loads(last_msg.content)
                        confirmation_text = tool_output.get("message", "Processed successfully.")
                    except Exception:
                        confirmation_text = str(last_msg.content)
                else:
                    confirmation_text = f"Action captured successfully: '{user_input}'"
                
                # Commit a visible UI state update message
                app.update_state(
                    config, 
                    {"messages": [AIMessage(content=confirmation_text)]}
                )
        else:
            # Standard conversational interaction execution
            result = stream_response(config=config, user_input=user_input, is_resume=False)

    # Cache sync processing sequence
    final_snapshot = app.get_state(config)
    updated_history = (
        final_snapshot.values.get("messages", [])
        if final_snapshot and final_snapshot.values
        else []
    )

    if updated_history:
        save_history_to_disk(st.session_state.thread_id, updated_history)

    st.session_state.processing = False
    st.rerun()