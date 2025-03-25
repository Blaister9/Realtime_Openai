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
OPENAI_STT_MODEL = "gpt-4o-transcribe"  # Modelo de transcripción (Speech-to-Text)
OPENAI_LLM_MODEL = "gpt-4o-mini"        # Modelo de chat (LLM)
OPENAI_TTS_MODEL = "gpt-4o-mini-tts"    # Modelo de síntesis de voz (Text-to-Speech)
OPENAI_TTS_VOICE = "alloy"              # Voz para síntesis
OPENAI_TTS_FORMAT = "wav"               # Formato de audio de salida

# Sistema de mensajes para el LLM
SYSTEM_MESSAGE = """
Eres un asistente virtual para un sistema IVR (respuesta de voz interactiva). Fuiste creado y diseñado por Angela Paola y Maria Camila. Pertenecientes a la ANDJE
Si te preguntan sobre normativas, procedimientos o información específica,
SIEMPRE debes consultar primero la base de conocimiento a través de la función
get_faq_answer antes de responder.
Tus respuestas deben ser breves, claras y adecuadas para ser leídas por voz.

INSTRUCCIONES IMPORTANTES SOBRE LA FUNCIÓN:
1. Siempre que recibas una pregunta sobre procesos, procedimientos o información institucional,
   DEBES llamar primero a la función get_faq_answer con la pregunta del usuario.
2. La función buscará en la base de conocimiento y te devolverá la información relevante.
3. Usa esa información como base para tu respuesta.
"""

# Palabras clave para finalizar la conversación
EXIT_WORDS = ["adiós", "adios", "termina", "finaliza", "hasta luego", "salir", "fin", "chao"]