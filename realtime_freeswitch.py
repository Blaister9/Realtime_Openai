#!/usr/bin/env python3
import sys
import requests
import base64
import json
import os
import logging
import time
import traceback
from dotenv import load_dotenv

# Cargar variables de entorno desde .env (mínimo cambio seguro)
load_dotenv('/home/sysadmin/encuesta_IVR/.env')


# Configurar logging extremadamente detallado
logging.basicConfig(
    level=logging.DEBUG,  # Cambiar a DEBUG para ver TODOS los mensajes
    format='%(asctime)s [%(levelname)s] [%(pathname)s:%(lineno)d] %(message)s',
    handlers=[
        logging.FileHandler("/home/sysadmin/encuesta_IVR/logs/asistente_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Anunciar inicio del script con información de diagnóstico
logger.info("==== INICIO DEL SCRIPT asistente_virtual.py ====")
logger.info(f"Versión de Python: {sys.version}")
logger.info(f"Ruta del ejecutable: {sys.executable}")
logger.info(f"Directorio actual: {os.getcwd()}")
logger.info(f"Variables de entorno: PATH={os.environ.get('PATH', 'No disponible')}")
logger.info(f"Argumentos: {sys.argv}")

# Intenta cargar FAISS pero no bloquea si falla
try:
    logger.info("Intentando importar numpy")
    import numpy as np
    logger.info("NumPy importado correctamente")

    # Añadir ruta base al path
    base_dir = "/home/sysadmin/encuesta_IVR"
    if base_dir not in sys.path:
        sys.path.append(base_dir)
        logger.info(f"Añadido {base_dir} al sys.path")

    logger.info("Intentando importar faiss_search desde embeddings.buscar_pregunta")
    from embeddings.buscar_pregunta import faiss_search
    logger.info("Módulo FAISS importado correctamente")
    FAISS_AVAILABLE = True
except ImportError as e:
    logger.error(f"Error importando módulos para FAISS: {e}")
    logger.error(traceback.format_exc())
    FAISS_AVAILABLE = False

def get_faq_answer(question):
    """Busca respuestas en la base de conocimiento usando FAISS"""
    logger.debug(f"Llamada a get_faq_answer con pregunta: {question[:100]}...")

    if not FAISS_AVAILABLE:
        logger.warning("FAISS no está disponible, omitiendo búsqueda de conocimiento")
        return None

    try:
        logger.info(f"Buscando en FAISS: {question[:100]}...")
        start_time = time.time()
        answer = faiss_search(question, threshold=0.5)
        search_time = time.time() - start_time
        logger.info(f"Búsqueda FAISS completada en {search_time:.2f} segundos")

        if answer:
            logger.info(f"Respuesta encontrada en FAISS: {str(answer)[:200]}...")
            return answer
        else:
            logger.info("No se encontró respuesta en FAISS")
            return None
    except Exception as e:
        logger.error(f"Error en búsqueda FAISS: {e}")
        logger.error(traceback.format_exc())
        return None

def main():
    logger.info("Entrando a función main()")

    if len(sys.argv) < 2:
        logger.error("Uso: asistente_virtual.py <ruta_wav>")
        sys.exit(1)

    user_input_wav = sys.argv[1]
    logger.info(f"Archivo de entrada: {user_input_wav}")

    if not os.path.exists(user_input_wav):
        logger.error(f"El archivo de audio no existe: {user_input_wav}")
        sys.exit(1)

    # Obtener estadísticas del archivo
    try:
        file_stats = os.stat(user_input_wav)
        logger.info(f"Estadísticas del archivo de entrada: tamaño={file_stats.st_size} bytes, modificado={time.ctime(file_stats.st_mtime)}")
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas del archivo: {e}")

    logger.info(f"Procesando archivo de audio: {user_input_wav}")

    try:
        logger.debug("Abriendo archivo de audio")
        with open(user_input_wav, "rb") as f:
            audio_bytes = f.read()
        logger.info(f"Archivo de audio leído correctamente: {len(audio_bytes)} bytes")
    except Exception as e:
        logger.error(f"No se pudo leer el archivo de audio: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        logger.error("La clave API de OpenAI no está configurada en las variables de entorno.")
        sys.exit(1)
    else:
        logger.info("API key de OpenAI configurada correctamente")

    # ------------------------------------------------------------
    # CUIDADO: NO ALTEREMOS LA LÓGICA FUNDAMENTAL DE ESTE CÓDIGO
    # ------------------------------------------------------------

    # Configuración de la solicitud a OpenAI
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    # Codificar el audio en base64
    encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
    logger.info(f"Audio codificado en base64: {len(encoded_audio)} caracteres")

    # Consultar FAISS si está disponible
    faiss_response = None
    if FAISS_AVAILABLE:
        # Aquí solo obtenemos información para diagnóstico - no alteramos la lógica
        logger.info("Realizando transcripción de prueba para diagnóstico de FAISS")
        try:
            # Este bloque es solo para diagnóstico, no cambia la lógica principal
            transcribe_url = "https://api.openai.com/v1/audio/transcriptions"
            transcribe_headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}

            with open(user_input_wav, "rb") as audio_file:
                files = {
                    "file": (os.path.basename(user_input_wav), audio_file, "audio/wav"),
                    "model": (None, "whisper-1")
                }

                logger.debug("Enviando solicitud de transcripción para diagnóstico")
                response = requests.post(transcribe_url, headers=transcribe_headers, files=files)

                if response.status_code == 200:
                    result = response.json()
                    transcript = result.get("text", "")
                    logger.info(f"Transcripción diagnóstica: {transcript[:100]}...")

                    # Solo para diagnóstico, consultamos FAISS
                    diag_faiss = get_faq_answer(transcript)
                    if diag_faiss:
                        logger.info("FAISS encontró una respuesta en la transcripción diagnóstica")
                    else:
                        logger.info("FAISS no encontró respuestas en la transcripción diagnóstica")
                else:
                    logger.warning(f"La transcripción diagnóstica falló: {response.status_code} - {response.text[:200]}")
        except Exception as e:
            logger.error(f"Error en transcripción diagnóstica: {e}")
            logger.error(traceback.format_exc())

    # INSTRUCCIONES PARA USAR FAISS
    system_message = """
    Eres un asistente virtual para un sistema IVR (respuesta de voz interactiva). Fuiste creado y diseñado por Angela Paola y Maria Camila. Pertenecientes a la ANDJE
    Si te preguntan sobre normativas, procedimientos o información específica,
    SIEMPRE debes consultar primero la base de conocimiento a través de la función
    get_faq_answer antes de responder.
    Tus respuestas deben ser breves, claras y adecuadas para ser leídas por voz.
    """

    # Añadir instrucciones específicas sobre FAISS
    system_message += """
    INSTRUCCIONES IMPORTANTES SOBRE LA FUNCIÓN:
    1. Siempre que recibas una pregunta sobre procesos, procedimientos o información institucional,
       DEBES llamar primero a la función get_faq_answer con la pregunta del usuario.
    2. La función buscará en la base de conocimiento y te devolverá la información relevante.
    3. Usa esa información como base para tu respuesta.
    """

    # Configurar payload principal
    payload = {
        "model": "gpt-4o-mini-audio-preview",
        "modalities": ["text", "audio"],  # Solo admite estas opciones
        "audio": {
            "voice": "alloy",
            "format": "wav"
        },
        "messages": [
            {
                "role": "system",
                "content": system_message
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "Analiza el audio y responde a mi consulta. Si es sobre procedimientos o información institucional, busca en la base de conocimiento antes de responder."
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": encoded_audio,
                            "format": "wav"
                        }
                    }
                ]
            }
        ],
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "get_faq_answer",
                    "description": "Busca respuestas en la base de conocimiento FAISS para preguntas sobre procedimientos, normativas o información institucional específica.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "La pregunta o consulta del usuario para buscar en la base de conocimiento"
                            }
                        },
                        "required": ["question"]
                    }
                }
            }
        ],
        # Esto fuerza a que el modelo intente usar la función
        "tool_choice": {
            "type": "function",
            "function": {
                "name": "get_faq_answer"
            }
        }
    }

    # Convertir el payload a JSON para inspección
    payload_json = json.dumps(payload, indent=2)
    logger.debug(f"Payload JSON para OpenAI: {payload_json[:500]}...")

    logger.info("Enviando solicitud a OpenAI...")

    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        request_time = time.time() - start_time
        logger.info(f"Solicitud a OpenAI completada en {request_time:.2f} segundos")

        logger.info(f"Código de estado de la respuesta: {response.status_code}")

        if response.status_code != 200:
            logger.error(f"Error en la solicitud a OpenAI: {response.status_code}")
            logger.error(f"Texto de respuesta: {response.text[:500]}...")
            sys.exit(1)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la solicitud a OpenAI: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    try:
        logger.debug("Analizando respuesta JSON de OpenAI")
        resp_json = response.json()
        logger.debug(f"Estructura de la respuesta: {list(resp_json.keys())}")

        # Verificar si hay llamada a función
        choices = resp_json.get("choices", [])
        logger.debug(f"Número de choices: {len(choices)}")

        if choices and "message" in choices[0]:
            message = choices[0]["message"]
            logger.debug(f"Contenido del mensaje: {list(message.keys())}")

            # Verificar si se llamó a la función
            if "tool_calls" in message:
                logger.info("Se detectó una llamada a función")
                tool_calls = message["tool_calls"]
                logger.debug(f"Número de tool_calls: {len(tool_calls)}")

                for tool_call in tool_calls:
                    if tool_call["function"]["name"] == "get_faq_answer":
                        logger.info("Se llamó a get_faq_answer")
                        try:
                            function_args = json.loads(tool_call["function"]["arguments"])
                            question = function_args.get("question", "")
                            logger.info(f"Pregunta para FAISS: {question[:100]}...")

                            # Llamar a la función FAISS
                            faiss_response = get_faq_answer(question)
                            logger.info(f"Respuesta de FAISS obtenida: {faiss_response is not None}")

                            # Preparar segunda llamada con el resultado
                            second_messages = [
                                {"role": "system", "content": system_message},
                                {"role": "user", "content": [
                                    {"type": "text", "text": "Analiza el audio y responde a mi consulta."},
                                    {"type": "input_audio", "input_audio": {"data": encoded_audio, "format": "wav"}}
                                ]},
                                {"role": "assistant", "content": None, "tool_calls": tool_calls}
                            ]

                            # Añadir el resultado de la función
                            second_messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call["id"],
                                "name": "get_faq_answer",
                                "content": json.dumps({
                                    "answer": faiss_response if faiss_response else "No se encontró información relacionada en nuestra base de conocimiento."
                                })
                            })

                            # Configurar segunda llamada
                            second_payload = {
                                "model": "gpt-4o-mini-audio-preview",
                                "modalities": ["text", "audio"],
                                "audio": {
                                    "voice": "alloy",
                                    "format": "wav"
                                },
                                "messages": second_messages
                            }

                            # Ejecutar segunda llamada
                            logger.info("Enviando segunda solicitud a OpenAI con resultado de FAISS...")
                            start_time = time.time()
                            second_response = requests.post(url, headers=headers, json=second_payload)
                            second_time = time.time() - start_time
                            logger.info(f"Segunda solicitud completada en {second_time:.2f} segundos")

                            if second_response.status_code != 200:
                                logger.error(f"Error en segunda solicitud: {second_response.status_code}")
                                logger.error(f"Texto de respuesta: {second_response.text[:500]}...")
                            else:
                                logger.info("Segunda solicitud exitosa, usando esta respuesta")
                                resp_json = second_response.json()
                        except Exception as e:
                            logger.error(f"Error procesando llamada a función: {e}")
                            logger.error(traceback.format_exc())
            else:
                logger.info("No se detectó llamada a función")

        # Extraer el texto para análisis de salida
        try:
            choices = resp_json.get("choices", [])
            if choices and "message" in choices[0]:
                message = choices[0]["message"]

                # Extraer texto de diferentes fuentes posibles
                transcript = ""
                if "content" in message and message["content"]:
                    transcript = message["content"]
                    logger.debug(f"Texto extraído de content: {transcript[:100]}...")
                elif "audio" in message and "transcript" in message["audio"]:
                    transcript = message["audio"]["transcript"]
                    logger.debug(f"Texto extraído de audio.transcript: {transcript[:100]}...")

                logger.info(f"Transcripción de la respuesta: {transcript[:100]}...")

                # Verificar si el usuario está pidiendo finalizar
                exit_words = ["adiós", "adios", "termina", "finaliza", "hasta luego", "salir", "fin", "chao"]
                if any(word in transcript.lower() for word in exit_words):
                    logger.info("Usuario solicitó finalizar la conversación")
                    with open("/home/sysadmin/encuesta_IVR/tmp/salir.flag", "w") as f:
                        f.write("1")
            else:
                logger.warning("No se encontró el mensaje en la respuesta")

        except Exception as e:
            logger.error(f"Error procesando texto de respuesta: {e}")
            logger.error(traceback.format_exc())

        # Extraer y decodificar el audio de respuesta
        try:
            audio_data = resp_json["choices"][0]["message"]["audio"]["data"]
            logger.info(f"Longitud de datos de audio codificados: {len(audio_data)} caracteres")

            audio_resp = base64.b64decode(audio_data)
            logger.info(f"Audio decodificado: {len(audio_resp)} bytes")
        except KeyError as e:
            logger.error(f"No se encontró la clave para el audio: {e}")
            logger.error(f"Estructura de respuesta disponible: {str(resp_json)[:500]}...")
            raise
        except Exception as e:
            logger.error(f"Error al procesar el audio de la respuesta: {e}")
            logger.error(traceback.format_exc())
            raise

    except KeyError as e:
        logger.error(f"No se encontró la clave esperada en la respuesta de OpenAI: {e}")
        logger.error(f"Respuesta completa: {response.text[:500]}...")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error al procesar la respuesta de OpenAI: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    # Guardar el audio de respuesta
    response_path = "/home/sysadmin/encuesta_IVR/tmp/assistant_response.wav"
    try:
        logger.debug(f"Guardando audio en {response_path}")
        with open(response_path, "wb") as f:
            f.write(audio_resp)

        # Verificar el archivo guardado
        if os.path.exists(response_path):
            file_size = os.path.getsize(response_path)
            logger.info(f"Respuesta generada y guardada en {response_path} (tamaño: {file_size} bytes)")

            # Establecer permisos adecuados
            try:
                os.chmod(response_path, 0o644)  # rw-r--r--
                logger.info(f"Permisos establecidos en el archivo de audio")
            except Exception as e:
                logger.warning(f"No se pudieron establecer permisos: {e}")
        else:
            logger.error(f"El archivo no existe después de guardar")
    except Exception as e:
        logger.error(f"No se pudo guardar el archivo de audio de respuesta: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    logger.info("==== FIN DEL SCRIPT asistente_virtual.py ====")

if __name__ == "__main__":
    try:
        # Crear directorios necesarios si no existen
        os.makedirs("/home/sysadmin/encuesta_IVR/logs", exist_ok=True)
        os.makedirs("/home/sysadmin/encuesta_IVR/tmp", exist_ok=True)

        main()
    except Exception as e:
        logger.critical(f"Excepción no controlada: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)
