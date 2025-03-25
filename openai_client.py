#!/usr/bin/env python3
import requests
import json
import logging
import time
import traceback
from config import (
    OPENAI_CHAT_URL,
    OPENAI_LLM_MODEL,
    SYSTEM_MESSAGE,
    EXIT_WORDS
)

logger = logging.getLogger(__name__)

def create_openai_headers(api_key):
    """
    Crea las cabeceras para la API de OpenAI
    
    Args:
        api_key (str): Clave API de OpenAI
        
    Returns:
        dict: Cabeceras HTTP para la API
    """
    return {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

def create_llm_payload(transcript, add_tools=True):
    """
    Crea el payload para la API de Chat Completions con el texto transcrito
    
    Args:
        transcript (str): Texto transcrito del audio
        add_tools (bool): Si es True, añade herramientas para la función get_faq_answer
        
    Returns:
        dict: Payload para la API
    """
    messages = [
        {
            "role": "system",
            "content": SYSTEM_MESSAGE
        },
        {
            "role": "user",
            "content": transcript
        }
    ]
    
    payload = {
        "model": OPENAI_LLM_MODEL,
        "messages": messages,
        "temperature": 0.4,
        "max_tokens": 350,
        "presence_penalty": -0.1  # Ligero desincentivo a repetirse
    }
    
    # Añadir herramientas para consultar la base de conocimiento si se requiere
    if add_tools:
        payload["tools"] = [
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
        ]
        
        # Forzar el uso de la función si es apropiado
        payload["tool_choice"] = {
            "type": "function",
            "function": {
                "name": "get_faq_answer"
            }
        }
    
    return payload

def create_second_llm_payload(transcript, tool_calls, tool_response):
    """
    Crea el payload para la segunda llamada a la API con resultados de la función
    
    Args:
        transcript (str): Texto transcrito del audio
        tool_calls (list): Lista de llamadas a herramientas de la primera respuesta
        tool_response (str): Respuesta de la función
        
    Returns:
        dict: Payload para la segunda llamada a la API
    """
    # Crear mensajes iniciales
    messages = [
        {"role": "system", "content": SYSTEM_MESSAGE},
        {"role": "user", "content": transcript},
        {"role": "assistant", "content": None, "tool_calls": tool_calls}
    ]
    
    # Añadir respuesta de la función
    for tool_call in tool_calls:
        if tool_call["function"]["name"] == "get_faq_answer":
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "name": "get_faq_answer",
                "content": json.dumps({
                    "answer": tool_response if tool_response else "No se encontró información relacionada en nuestra base de conocimiento."
                })
            })
    
    # Crear payload completo
    return {
        "model": OPENAI_LLM_MODEL,
        "messages": messages,
        "temperature": 0.7  # Ajustar según necesidad
    }

def send_openai_request(headers, payload, url=OPENAI_CHAT_URL):
    """
    Envía una solicitud a la API de OpenAI
    
    Args:
        headers (dict): Cabeceras HTTP
        payload (dict): Payload de la solicitud
        url (str): URL del endpoint de la API
        
    Returns:
        dict or None: Respuesta JSON o None si hay error
    """
    try:
        # Convertir payload a JSON para log
        payload_json = json.dumps(payload, indent=2)
        logger.debug(f"Payload JSON para OpenAI: {payload_json[:500]}...")
        
        logger.info(f"Enviando solicitud a OpenAI: {url}")
        start_time = time.time()
        response = requests.post(url, headers=headers, json=payload)
        request_time = time.time() - start_time
        logger.info(f"Solicitud a OpenAI completada en {request_time:.2f} segundos")
        
        logger.info(f"Código de estado de la respuesta: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Error en la solicitud a OpenAI: {response.status_code}")
            logger.error(f"Texto de respuesta: {response.text[:500]}...")
            return None
            
        return response.json()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error en la solicitud a OpenAI: {e}")
        logger.error(traceback.format_exc())
        return None

def process_llm_response(resp_json):
    """
    Procesa la respuesta del LLM para extraer información importante
    
    Args:
        resp_json (dict): Respuesta JSON de OpenAI
        
    Returns:
        tuple: (tool_calls, assistant_response, should_exit)
            - tool_calls: Llamadas a herramientas o None
            - assistant_response: Texto de la respuesta del asistente
            - should_exit: Booleano que indica si se debe salir
    """
    tool_calls = None
    assistant_response = ""
    should_exit = False
    
    try:
        # Verificar si hay choices
        choices = resp_json.get("choices", [])
        logger.debug(f"Número de choices: {len(choices)}")
        
        if choices and "message" in choices[0]:
            message = choices[0]["message"]
            logger.debug(f"Contenido del mensaje: {list(message.keys())}")
            
            # Extraer llamadas a función si existen
            if "tool_calls" in message:
                logger.info("Se detectó una llamada a función")
                tool_calls = message["tool_calls"]
                logger.debug(f"Número de tool_calls: {len(tool_calls)}")
            
            # Extraer texto de respuesta
            if "content" in message and message["content"]:
                assistant_response = message["content"]
                logger.debug(f"Texto de respuesta: {assistant_response[:100]}...")
            
            # Verificar si el usuario está pidiendo finalizar
            if any(word in assistant_response.lower() for word in EXIT_WORDS):
                logger.info("Usuario solicitó finalizar la conversación")
                should_exit = True
        
    except Exception as e:
        logger.error(f"Error procesando respuesta de OpenAI: {e}")
        logger.error(traceback.format_exc())
    
    return tool_calls, assistant_response, should_exit

def extract_function_args(tool_call):
    """
    Extrae los argumentos de una llamada a función
    
    Args:
        tool_call (dict): Información de llamada a función
        
    Returns:
        str or None: Argumento de pregunta o None si hay error
    """
    try:
        function_args = json.loads(tool_call["function"]["arguments"])
        question = function_args.get("question", "")
        logger.info(f"Pregunta para FAISS: {question[:100]}...")
        return question
    except Exception as e:
        logger.error(f"Error extrayendo argumentos de función: {e}")
        logger.error(traceback.format_exc())
        return None