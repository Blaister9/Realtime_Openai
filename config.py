#!/usr/bin/env python3
import os
import sys
import logging
import time
from dotenv import load_dotenv

def setup_environment():
    """Configura el entorno, carga variables y configura logging"""
    # Crear directorios necesarios
    os.makedirs(os.path.join(BASE_DIR, "logs"), exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "tmp"), exist_ok=True)
    
    # Cargar variables de entorno
    load_dotenv(os.path.join(BASE_DIR, '.env'))
    
    # Configurar logging extremadamente detallado
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] [%(pathname)s:%(lineno)d] %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(BASE_DIR, "logs/asistente_debug.log")),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Anunciar inicio con información de diagnóstico
    logger.info("==== INICIO DE LA CONFIGURACIÓN ====")
    logger.info(f"Versión de Python: {sys.version}")
    logger.info(f"Ruta del ejecutable: {sys.executable}")
    logger.info(f"Directorio actual: {os.getcwd()}")
    logger.info(f"Directorio base: {BASE_DIR}")
    logger.info(f"Variables de entorno: PATH={os.environ.get('PATH', 'No disponible')}")
    
    # Verificar clave API
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("La clave API de OpenAI no está configurada en las variables de entorno.")
        return False
    else:
        logger.info("API key de OpenAI configurada correctamente")
        
    # Añadir ruta base al path si no está
    if BASE_DIR not in sys.path:
        sys.path.append(BASE_DIR)
        logger.info(f"Añadido {BASE_DIR} al sys.path")
    
    return True

# Definición de constantes
BASE_DIR = "/home/sysadmin/encuesta_IVR"
TMP_DIR = os.path.join(BASE_DIR, "tmp")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
RESPONSE_PATH = os.path.join(TMP_DIR, "assistant_response.wav")
EXIT_FLAG_PATH = os.path.join(TMP_DIR, "salir.flag")

# URLs y endpoints
OPENAI_API_BASE_URL = "https://api.openai.com/v1"
OPENAI_CHAT_URL = f"{OPENAI_API_BASE_URL}/chat/completions"
OPENAI_TRANSCRIBE_URL = f"{OPENAI_API_BASE_URL}/audio/transcriptions"
OPENAI_SPEECH_URL = f"{OPENAI_API_BASE_URL}/audio/speech"

# Modelos y configuración de OpenAI
# Arquitectura encadenada (STT → LLM → TTS)
OPENAI_STT_MODEL = "gpt-4o-mini-transcribe"  # Modelo de transcripción (Speech-to-Text)
OPENAI_LLM_MODEL = "gpt-4o-mini"        # Modelo de chat (LLM)
OPENAI_TTS_MODEL = "gpt-4o-mini-tts"    # Modelo de síntesis de voz (Text-to-Speech)
OPENAI_TTS_VOICE = "alloy"              # Voz para síntesis
OPENAI_TTS_FORMAT = "wav"               # Formato de audio de salida

# Sistema de mensajes para el LLM (optimizado para concisión)
SYSTEM_MESSAGE = """
Eres un asistente virtual para un sistema IVR (respuesta de voz interactiva). Fuiste creado por Angela Paola y Maria Camila de la ANDJE.

REGLAS IMPORTANTES:
1. Sé extremadamente conciso. Respuestas ideales: 1-3 frases.
2. SOLO busca en la base de conocimiento cuando te pregunten específicamente sobre normativas, procedimientos o información institucional.
3. No proporciones información extra o no solicitada.
4. Habla en un lenguaje claro y sencillo, ideal para ser escuchado por teléfono.
5. Si no tienes información específica, responde brevemente sin disculparte en exceso.

EJEMPLOS DE RESPUESTAS BUENAS:
Pregunta: "Hola, ¿cómo estás?"
Respuesta: "Hola, estoy bien. ¿En qué puedo ayudarte hoy?"

Pregunta: "¿Cuál es tu nombre?"
Respuesta: "Soy el asistente virtual de la ANDJE, creado por Angela Paola y Maria Camila."
"""

# Palabras clave para finalizar la conversación
EXIT_WORDS = ["adiós", "adios", "termina", "finaliza", "hasta luego", "salir", "fin", "chao"]