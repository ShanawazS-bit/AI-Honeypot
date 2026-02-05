from sentence_transformers import SentenceTransformer
import os

print("Downloading Sentence Transformer Model during build...")
# Force download to default cache
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("Model downloaded successfully.")
