import os

# Use /tmp for Railway compatibility
os.environ["HF_HOME"] = "/tmp"

print("Downloading Sentence Transformer Model during build...")
# Force download to /tmp cache
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
print("Model downloaded successfully.")
