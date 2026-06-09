from langchain_huggingface import HuggingFaceEmbeddings
embeddings=HuggingFaceEmbeddings(
    model_name="BAAI/bge-large-en-v1.5"
)