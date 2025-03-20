import os
import sys
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

# ----------------------------
# CARGA DE RECURSOS GLOBALES
# ----------------------------
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)

model = SentenceTransformer("sentence-transformers/multi-qa-mpnet-base-dot-v1")
index = faiss.read_index(os.path.join(current_dir, "faiss_index.bin"))

with open(os.path.join(current_dir, "preguntas_lista.json"), "r", encoding="utf-8") as f:
    faiss_questions = json.load(f)

with open(os.path.join(root_dir, "preguntas.json"), "r", encoding="utf-8") as f:
    preguntas_db = json.load(f)

# ----------------------------
# FUNCION PRINCIPAL DE FAISS
# ----------------------------
def faiss_search(pregunta_usuario, threshold=0.5, k_value=3):
    """
    Retorna una lista de strings (cada string es la 'respuesta' de la FAQ),
    con hasta k_value resultados que pasen el threshold.
    """
    try:
        # 1) Generar embedding
        embedding = model.encode([pregunta_usuario], convert_to_numpy=True)
        
        # 2) Buscar en FAISS con k_value
        D, I = index.search(embedding, k=k_value)
        
        # 3) Recopilar resultados
        respuestas = []
        for rank in range(k_value):
            idx = I[0][rank]
            sim = D[0][rank]
            
            # Debug para ver en consola
            print(f"Top {rank+1} -> idx={idx}, score={sim}")
            
            # Si no supera threshold o idx no es válido, paramos
            if idx < 0 or sim < threshold:
                break
            
            # Recuperar la 'pregunta' con la que indexamos en preguntas_lista.json
            faiss_pregunta = faiss_questions[idx].strip().lower()
            
            # Debug extra
            print(f"Rank={rank}, Score={sim}, Pregunta='{faiss_pregunta}'")
            
            # Buscar en preguntas.json la respuesta asociada
            for item in preguntas_db["preguntas"]:
                if item["pregunta"].strip().lower() == faiss_pregunta:
                    # Agregamos SOLO la respuesta (para no meter tokens extra)
                    respuestas.append(item["respuesta"])
                    break
        
        return respuestas

    except Exception as e:
        print(f"[ERROR] en faiss_search: {str(e)}", file=sys.stderr)
        return []

# --------------------------------
# EJECUCION EN TERMINAL (TEST)
# --------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Debes proporcionar una pregunta como argumento.", file=sys.stderr)
        sys.exit(1)
    
    user_query = sys.argv[1]
    k = 2
    resultado = faiss_search(user_query, threshold=0.5, k_value=k)
    
    if resultado:
        # Mostramos solo el top-1 en consola
        print("\n=== RESPUESTA (TOP-1) ===")
        print(resultado[0])
    else:
        print("No tengo información sobre eso.")
