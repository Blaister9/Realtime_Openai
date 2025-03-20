import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import os

# =====================
# CONFIGURACIONES
# =====================
EMBEDDINGS_MODEL = "sentence-transformers/multi-qa-mpnet-base-dot-v1"
JSON_FILE_PATH = "../preguntas.json"
INDEX_FILE_PATH = "faiss_index.bin"
MAPPING_FILE_PATH = "preguntas_lista.json"

# =====================
# CARGAR MODELO DE EMBEDDINGS
# =====================
model = SentenceTransformer(EMBEDDINGS_MODEL)

# =====================
# CARGAR Y PROCESAR DATOS
# =====================
with open(JSON_FILE_PATH, "r", encoding="utf-8") as file:
    preguntas_db = json.load(file)

# Extraer información relevante (preguntas, respuestas y metadatos)
preguntas = []
mapeo_preguntas = {}  # Para mapear índices a preguntas originales

preguntas_lista = preguntas_db["preguntas"]

for idx, item in enumerate(preguntas_lista):
    pregunta = item["pregunta"].strip().lower()
    respuesta = item["respuesta"].strip()
    metadata = item.get("metadata", {})

    preguntas.append(pregunta)
    mapeo_preguntas[idx] = {
        "pregunta": pregunta,
        "respuesta": respuesta,
        "metadata": metadata,
        "url": item.get("url", ""),
    }

# =====================
# CREAR EMBEDDINGS
# =====================
print("🔄 Generando embeddings...")
embeddings = model.encode(preguntas, convert_to_numpy=True, normalize_embeddings=True)

# =====================
# CREAR ÍNDICE FAISS
# =====================
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)  # IP: Producto Interno (mejor para embeddings normalizados)
index.add(embeddings)

# =====================
# GUARDAR ÍNDICE Y LISTA DE PREGUNTAS
# =====================
faiss.write_index(index, INDEX_FILE_PATH)

# Guardar solo la lista de preguntas para asegurar compatibilidad con FAISS
with open(MAPPING_FILE_PATH, "w", encoding="utf-8") as f:
    json.dump(preguntas, f, ensure_ascii=False, indent=4)

# Guardar el mapeo completo en otro archivo
with open("preguntas_mapeo.json", "w", encoding="utf-8") as f:
    json.dump(mapeo_preguntas, f, ensure_ascii=False, indent=4)

print(f"✅ FAISS indexado con éxito. Total de preguntas indexadas: {len(preguntas)}")
