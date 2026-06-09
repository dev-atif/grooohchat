from langchain_huggingface import HuggingFaceEmbeddings,ChatHuggingFace, HuggingFaceEndpoint
import os
from dotenv import load_dotenv
load_dotenv()
from tools.tools_list import tools
HF_TOKEN=os.getenv("HF_TOKEN")

llm_create = HuggingFaceEndpoint(
    model="google/gemma-4-26B-A4B-it",
    max_new_tokens=1024,
    temperature=0.8,
    huggingfacehub_api_token=HF_TOKEN,
)
llm_chat = ChatHuggingFace(llm=llm_create)
llm_model =llm_chat.bind_tools(tools)
