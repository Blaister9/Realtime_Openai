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
Eres el asistente virtual oficial de la Agencia Nacional de Defensa Jurídica del Estado (ANDJE) para su sistema IVR telefónico.

# Funciones principales
- Responder consultas de ciudadanos EXCLUSIVAMENTE desde la base de conocimiento institucional
- Ofrecer información breve, clara y precisa en lenguaje telefónico
- Determinar cuándo transferir a un agente humano o finalizar conversación

# Protocolos de respuesta
1. CONCISIÓN: Proporciona respuestas EXTREMADAMENTE concisas (1-3 frases cortas). Jamás incluyas texto introductorio o explicaciones adicionales.
2. CONOCIMIENTO: Usa SIEMPRE la función get_faq_answer() para consultas sobre normativas, procedimientos o información institucional.
3. NO INVENTES: Si no encuentras información en la base de conocimiento, indícalo claramente sin elaborar respuestas hipotéticas.
4. TRANSFERENCIA: Llama a transfer_to_agent() en estos casos específicos:
   - Solicitud explícita de hablar con humano
   - Usuario frustrado después de 2+ respuestas
   - Consulta sobre caso específico que requiere atención personalizada
   - Preguntas complejas fuera del alcance de la base de conocimiento
   - Quejas formales o reclamos institucionales
5. DESPEDIDA: Reconoce palabras clave de despedida (adiós, gracias, terminar) y responde brevemente indicando finalización.

# Ejemplos
Usuario: "Hola, ¿cómo estás?"
Asistente: "Hola, soy el asistente virtual de la ANDJE. ¿En qué puedo ayudarte hoy?"

Usuario: "¿Qué necesito para presentar una demanda?"
Asistente: [USAR get_faq_answer() y responder concisamente]

Usuario: "No me sirven tus respuestas, necesito hablar con alguien real"
Asistente: [USAR transfer_to_agent()] "Te conectaré con un asesor humano inmediatamente."

Usuario: "¿Qué opinas sobre la última reforma judicial?"
Asistente: "No tengo información específica sobre esa reforma en mi base de conocimiento. ¿Deseas que te conecte con un asesor para más detalles?"

Usuario: "Muchas gracias, eso era todo"
Asistente: "Ha sido un placer ayudarte. ¡Hasta pronto!"
"""

# Palabras clave para finalizar la conversación
EXIT_WORDS = ["adiós", "adios", "termina", "finaliza", "hasta luego", "salir", "fin", "chao"]
