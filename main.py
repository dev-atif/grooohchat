import os
import json
import uuid
import base64
import streamlit as st
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage
from utils.schema_type import ChatState
from workflow.workflow import app

load_dotenv()

# =====================================================
# STREAMLIT CONFIG
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
# CACHE SYSTEM
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
# THREAD ID
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
# LOAD HISTORY
# =====================================================
state_snapshot = app.get_state(config)

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
# BOOTSTRAP
# =====================================================
if not history:
    init_state = ChatState(question="", messages=[])

    with st.spinner("Initializing..."):
        app.invoke(init_state, config=config)

    snapshot = app.get_state(config)
    history = snapshot.values.get("messages", []) if snapshot and snapshot.values else []

    save_history_to_disk(st.session_state.thread_id, history)
    st.rerun()

# =====================================================
# HEADER
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
# CHAT HISTORY
# =====================================================
for msg in history:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user", avatar="user.png"):
            st.markdown(msg.content)

    elif isinstance(msg, (AIMessage, AIMessageChunk)):
        if msg.content:
            with st.chat_message("assistant", avatar="logofavicon.png"):
                st.markdown(f'<div class="assistant-red-box">{msg.content}</div>', unsafe_allow_html=True)

# =====================================================
# STREAMING (FIXED — NO DOUBLE RENDER, NO FLICKER)
# =====================================================
def stream_response(state_input, config):
    box = None
    full_text = ""

    for msg, metadata in app.stream(
        state_input,
        config=config,
        stream_mode="messages",
    ):
        if isinstance(msg, ToolMessage):
            continue

        if isinstance(msg, (AIMessage, AIMessageChunk)) and msg.content:
            full_text += msg.content

            # create assistant UI ONLY ONCE
            if box is None:
                box = st.chat_message("assistant", avatar="logofavicon.png").empty()

            box.markdown(
                f'<div class="assistant-red-box">{full_text}</div>',
                unsafe_allow_html=True,
            )

    # IMPORTANT: return only (NO re-render outside)
    return full_text

# =====================================================
# INPUT
# =====================================================
def disable_input():
    st.session_state.processing = True

user_input = st.chat_input(
    "Ask anything",
    disabled=st.session_state.processing,
    on_submit=disable_input,
)

if st.session_state.processing and user_input:

    # user message
    with st.chat_message("user", avatar="user.png"):
        st.markdown(user_input)

    state_input = ChatState(
        question=user_input,
        messages=[HumanMessage(content=user_input)],
    )

    # STREAM ONLY (NO SECOND ASSISTANT RENDER AFTER THIS)
    with st.spinner("Streaming response..."):
        result = stream_response(state_input, config)

    # SAVE STATE ONLY (NO UI RERENDER OF ASSISTANT)
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