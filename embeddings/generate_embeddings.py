import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Cargar modelo Sentence-Transformers
model = SentenceTransformer("sentence-transformers/multi-qa-mpnet-base-dot-v1")

# Cargar preguntas desde preguntas.json
with open("../preguntas.json", "r", encoding="utf-8") as file:
    preguntas_db = json.load(file)

preguntas = list(preguntas_db.keys())

# Convertir preguntas a embeddings
embeddings = model.encode(preguntas, convert_to_numpy=True)

# Crear índice FAISS (L2 - Euclidean Distance)
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

# Guardar índice y preguntas
faiss.write_index(index, "faiss_index.bin")
with open("preguntas_lista.json", "w", encoding="utf-8") as f:
    json.dump(preguntas, f)

print("✅ FAISS indexado con éxito. Total de preguntas:", len(preguntas))
