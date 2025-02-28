import os
import sys
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# Precargar recursos una sola vez al importar el módulo
# ======================================================

# Configurar paths
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)

# Cargar modelo y datos
model = SentenceTransformer("sentence-transformers/multi-qa-mpnet-base-dot-v1")
index = faiss.read_index(os.path.join(current_dir, "faiss_index.bin"))

# Cargar preguntas
with open(os.path.join(current_dir, "preguntas_lista.json"), "r", encoding="utf-8") as f:
    preguntas = json.load(f)

with open(os.path.join(root_dir, "preguntas.json"), "r", encoding="utf-8") as f:
    preguntas_db = json.load(f)

# Función principal
# ==================
def faiss_search(pregunta_usuario, threshold=0.5):
    try:
        # Generar embedding
        embedding = model.encode([pregunta_usuario], convert_to_numpy=True)
        
        # Buscar en FAISS
        D, I = index.search(embedding, k=1)
        
        # Procesar resultados
        if I[0][0] < 0 or D[0][0] < threshold:
            return None
        
        mejor_pregunta = preguntas[I[0][0]].strip().lower()
        
        # Buscar en la base de datos completa
        for item in preguntas_db:
            if item["content"]["pregunta"].strip().lower() == mejor_pregunta:
                return item["content"]["respuesta"]
        
        return None
    
    except Exception as e:
        print(f"Error en FAISS: {str(e)}", file=sys.stderr)
        return None

# Mantener compatibilidad con ejecución directa
# ============================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Debes proporcionar una pregunta como argumento.", file=sys.stderr)
        sys.exit(1)
    
    respuesta = faiss_search(sys.argv[1])
    
    if respuesta:
        sys.stdout.buffer.write(respuesta.encode('utf-8') + b'\n')
    else:
        print("No tengo información sobre eso.")