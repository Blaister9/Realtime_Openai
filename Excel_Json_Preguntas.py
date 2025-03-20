import pandas as pd
import json

def excel_to_json(excel_path, json_output_path):
    """
    Convierte un archivo Excel en un JSON estructurado para FAISS.
    
    Parámetros:
        - excel_path (str): Ruta del archivo Excel.
        - json_output_path (str): Ruta de salida del JSON.
    """
    # Leer el archivo Excel (asumiendo que solo tiene una hoja relevante)
    df = pd.read_excel(excel_path, skiprows=1, usecols="A:B", names=["pregunta", "respuesta"])
    
    # Convertir a lista de diccionarios
    data = {"preguntas": []}
    
    for _, row in df.iterrows():
        data["preguntas"].append({
            "pregunta": row["pregunta"],
            "respuesta": row["respuesta"],
            "metadata": {}  # Espacio para futuras mejoras
        })
    
    # Guardar como JSON
    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    print(f"✅ Conversión completada. JSON guardado en: {json_output_path}")

# Ejemplo de uso
excel_to_json(r"C:\Users\edwin.paz\Documents\Asistente_AtencionCiudadano\Realtime_Openai\preguntas primer nivel de servicio.xlsx", "preguntas.json")
