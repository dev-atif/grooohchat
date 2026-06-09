from langchain_pinecone import PineconeVectorStore
import os
from dotenv import load_dotenv
from utils.embedings import embeddings
load_dotenv()
PICONE_API_KEY=os.getenv("PINE_CONE_API_KEY")
vectorstore=PineconeVectorStore(index_name="groooh",embedding=embeddings,pinecone_api_key=PICONE_API_KEY)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})