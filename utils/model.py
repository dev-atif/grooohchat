from langchain_huggingface import HuggingFaceEmbeddings,ChatHuggingFace, HuggingFaceEndpoint
import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
load_dotenv()
from tools.tools_list import tools
HF_TOKEN=os.getenv("HF_TOKEN")

llm_create =ChatOpenAI(
    model="openai/gpt-4o-mini",
    base_url="https://openrouter.ai/api/v1",
    api_key=HF_TOKEN,
    temperature=0.8,
    max_tokens=1024,
)

llm_model =llm_create.bind_tools(tools)
