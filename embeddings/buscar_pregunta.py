import os
import sys
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Cargar modelo
model = SentenceTransformer("sentence-transformers/multi-qa-mpnet-base-dot-v1")

# Obtener directorios correctos
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)

index_path = os.path.join(current_dir, "faiss_index.bin")
preguntas_lista_path = os.path.join(current_dir, "preguntas_lista.json")
preguntas_json_path = os.path.join(root_dir, "preguntas.json")

# Verificar que los archivos existen antes de cargarlos
if not os.path.exists(index_path):
    print("Error: No se encontró 'faiss_index.bin'.")
    sys.exit(1)

if not os.path.exists(preguntas_lista_path):
    print("Error: No se encontró 'preguntas_lista.json'.")
    sys.exit(1)

if not os.path.exists(preguntas_json_path):
    print(f"Error: No se encontró 'preguntas.json' en {preguntas_json_path}.")
    sys.exit(1)

# Cargar FAISS y preguntas
index = faiss.read_index(index_path)
preguntas = json.load(open(preguntas_lista_path, encoding="utf-8"))

# Obtener la pregunta del usuario
if len(sys.argv) < 2:
    print("Error: No se proporcionó una pregunta.")
    sys.exit(1)

pregunta_usuario = sys.argv[1]

# Generar embedding de la pregunta
embedding_usuario = model.encode([pregunta_usuario], convert_to_numpy=True)

# Buscar en FAISS
D, I = index.search(embedding_usuario, k=1)

# Extraer mejor resultado
mejor_indice = int(I[0][0])
similitud = D[0][0]

if mejor_indice < 0 or similitud < 0.5:
    print("Lo siento, no tengo una respuesta para esa pregunta.")
    sys.exit(0)

# Extraer la mejor pregunta encontrada
mejor_pregunta = preguntas[mejor_indice]

# Cargar todas las preguntas desde el JSON original
with open(preguntas_json_path, "r", encoding="utf-8") as file:
    preguntas_db = json.load(file)

# Buscar la pregunta en el JSON original
respuesta = None
for item in preguntas_db:
    if item["content"]["pregunta"].strip().lower() == mejor_pregunta:
        respuesta = item["content"]["respuesta"]
        break

# Si no se encuentra, devolver mensaje de error
if respuesta:
    print(respuesta)
else:
    print("No tengo información sobre eso.")

