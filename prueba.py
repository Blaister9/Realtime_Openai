import json

with open(r"C:\Users\edwin.paz\Documents\Asistente_AtencionCiudadano\Realtime_Openai\embeddings\preguntas_lista.json", "r", encoding="utf-8") as f:
    preguntas = json.load(f)

print(type(preguntas))  # Debe ser <class 'list'>
print(len(preguntas))   # Debe coincidir con el número de preguntas indexadas
print(preguntas[:5])    # Muestra las primeras preguntas para verificar
