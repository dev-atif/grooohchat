import os
import uuid
import base64
import streamlit as st
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, AIMessage, AIMessageChunk, ToolMessage
from langgraph.types import Command  
from utils.schema_type import ChatState
from workflow.workflow import app

load_dotenv()

# =====================================================
# CONFIG
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
# STREAM RESPONSE
# =====================================================
def stream_response(config, user_input=None, is_resume=False):
    box = None
    full_text = ""

    if is_resume:
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

            # box.markdown(
            #     f'<div class="assistant-red-box">{full_text}</div>',
            #     unsafe_allow_html=True,
            # )
            box.markdown(full_text)

    return full_text


# =====================================================
# SESSION STATE
# =====================================================
if "thread_id" not in st.session_state:
    tid = st.query_params.get("tid")
    st.session_state.thread_id = tid if tid else str(uuid.uuid4())[:8]
    st.query_params["tid"] = st.session_state.thread_id

if "processing" not in st.session_state:
    st.session_state.processing = False

if "show_quick_actions" not in st.session_state:
    st.session_state.show_quick_actions = True

if "has_started_chat" not in st.session_state:
    st.session_state.has_started_chat = False

# 🔥 EXECUTION QUEUE (CRITICAL FIX)
if "exec_queue" not in st.session_state:
    st.session_state.exec_queue = None

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# =====================================================
# STATE SNAPSHOT
# =====================================================
state_snapshot = app.get_state(config)

active_interrupts = (
    state_snapshot.tasks[0].interrupts if state_snapshot.tasks else []
)

history = []
if state_snapshot and state_snapshot.values:
    history = state_snapshot.values.get("messages", [])

# =====================================================
# INIT
# =====================================================
if "ui_initialized" not in st.session_state:
    st.session_state.ui_initialized = True
    st.session_state.has_started_chat = False
    st.session_state.show_quick_actions = True

    if history:
        st.session_state.has_started_chat = True
        st.session_state.show_quick_actions = False

if not history:
    init_state = ChatState(question="", messages=[])

    with st.spinner("Initializing Workspace Engine..."):
        app.invoke(init_state, config=config)

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
                # st.markdown(
                #     f'<div class="assistant-red-box">{msg.content}</div>',
                #     unsafe_allow_html=True
                # )
                st.markdown(msg.content)

# =====================================================
# QUICK ACTIONS (NO RERUN HERE)
# =====================================================
QUICK_ACTIONS = [
    ("🌐 Website", "I want a website"),
    ("🎨 Branding", "I want branding"),
    ("🖼️ Logo", "I want a logo"),
    ("✨ UI/UX", "I want UI/UX design"),
    ("🤖 AI App", "I want an AI application"),
    ("📱 Mobile App", "I want a mobile app"),
    ("🚀 Landing Page", "I want a landing page"),
    ("💬 Consultation", "I need consultation"),
]

show_quick = (
    st.session_state.show_quick_actions
    and not st.session_state.has_started_chat
)

if show_quick:
    cols = st.columns(4)

    for i, (label, prompt) in enumerate(QUICK_ACTIONS):
        with cols[i % 4]:
            if st.button(label, key=f"qa_{i}", use_container_width=True):

                # ONLY STORE REQUEST (NO RERUN)
                st.session_state.exec_queue = prompt
                st.session_state.show_quick_actions = False
                st.session_state.has_started_chat = True

# =====================================================
# CHAT INPUT (SAFE)
# =====================================================
user_input = st.chat_input(
    "Reply..." if active_interrupts else "Ask anything",
    disabled=st.session_state.processing
)

if user_input:

    st.session_state.has_started_chat = True
    st.session_state.show_quick_actions = False
    st.session_state.exec_queue = user_input

# =====================================================
# EXECUTION ENGINE (CRITICAL FIX)
# =====================================================
if st.session_state.exec_queue:

    prompt = st.session_state.exec_queue
    st.session_state.exec_queue = None
    st.session_state.processing = True

    with st.chat_message("user", avatar="user.png"):
        st.markdown(prompt)

    with st.spinner("Processing..."):
        if active_interrupts:
            stream_response(config, prompt, is_resume=True)
        else:
            stream_response(config, prompt, is_resume=False)

    st.session_state.processing = False

    st.rerun()

# =====================================================
# INTERRUPTS
# =====================================================
if active_interrupts:
    interrupt_info = active_interrupts[0].value
    interrupt_msg = (
        interrupt_info.get("message")
        if isinstance(interrupt_info, dict)
        else str(interrupt_info)
    )

    with st.chat_message("assistant", avatar="logofavicon.png"):
                st.markdown(
                    f'<div class="assistant-red-box">{interrupt_msg}</div>',
                    unsafe_allow_html=True
                )