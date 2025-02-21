import sys
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Cargar modelo
model = SentenceTransformer("sentence-transformers/multi-qa-mpnet-base-dot-v1")

# Cargar índice FAISS y lista de preguntas
index = faiss.read_index("faiss_index.bin")
preguntas = json.load(open("preguntas_lista.json", encoding="utf-8"))

# Obtener la pregunta del usuario desde argumentos de consola
pregunta_usuario = sys.argv[1]

# Generar embedding de la pregunta del usuario
embedding_usuario = model.encode([pregunta_usuario], convert_to_numpy=True)

# Buscar en FAISS
D, I = index.search(embedding_usuario, k=1)  # k=1 → Obtener la mejor coincidencia

# Extraer mejor resultado
mejor_indice = I[0][0]
similitud = D[0][0]
mejor_pregunta = preguntas[mejor_indice]

# Si la similitud es alta, devolver la respuesta, si no, indicar que no hay resultado
if similitud < 0.5:
    print("Lo siento, no tengo una respuesta para esa pregunta.")
else:
    with open("../preguntas.json", "r", encoding="utf-8") as file:
        preguntas_db = json.load(file)
    print(preguntas_db[mejor_pregunta])
