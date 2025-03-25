#!/usr/bin/env python3
import os
import base64
import logging
import time
import requests
import traceback
import json
from config import OPENAI_TRANSCRIBE_URL, OPENAI_STT_MODEL, OPENAI_SPEECH_URL, OPENAI_TTS_MODEL, OPENAI_TTS_VOICE, OPENAI_TTS_FORMAT

logger = logging.getLogger(__name__)

def validate_audio_file(audio_path):
    """
    Valida que el archivo de audio exista y obtiene sus estadísticas
    
    Args:
        audio_path (str): Ruta al archivo de audio
        
    Returns:
        bool: True si el archivo es válido, False en caso contrario
    """
    if not os.path.exists(audio_path):
        logger.error(f"El archivo de audio no existe: {audio_path}")
        return False
        
    # Obtener estadísticas del archivo
    try:
        file_stats = os.stat(audio_path)
        logger.info(f"Estadísticas del archivo de entrada: tamaño={file_stats.st_size} bytes, modificado={time.ctime(file_stats.st_mtime)}")
        return True
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas del archivo: {e}")
        return False

def read_audio_file(audio_path):
    """
    Lee un archivo de audio y lo retorna como bytes
    
    Args:
        audio_path (str): Ruta al archivo de audio
        
    Returns:
        bytes or None: Contenido del archivo como bytes o None si hay error
    """
    try:
        logger.debug(f"Abriendo archivo de audio: {audio_path}")
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        logger.info(f"Archivo de audio leído correctamente: {len(audio_bytes)} bytes")
        return audio_bytes
    except Exception as e:
        logger.error(f"No se pudo leer el archivo de audio: {e}")
        logger.error(traceback.format_exc())
        return None

def encode_audio_base64(audio_bytes):
    """
    Codifica los bytes de audio en base64
    
    Args:
        audio_bytes (bytes): Bytes de audio
        
    Returns:
        str: Audio codificado en base64
    """
    encoded_audio = base64.b64encode(audio_bytes).decode("utf-8")
    logger.info(f"Audio codificado en base64: {len(encoded_audio)} caracteres")
    return encoded_audio

def decode_audio_base64(base64_string):
    """
    Decodifica una cadena base64 a bytes de audio
    
    Args:
        base64_string (str): Audio codificado en base64
        
    Returns:
        bytes: Bytes de audio decodificados
    """
    try:
        audio_bytes = base64.b64decode(base64_string)
        logger.info(f"Audio decodificado: {len(audio_bytes)} bytes")
        return audio_bytes
    except Exception as e:
        logger.error(f"Error al decodificar audio base64: {e}")
        logger.error(traceback.format_exc())
        raise

def transcribe_audio(audio_path, api_key):
    """
    Transcribe un archivo de audio a texto usando la API de OpenAI (gpt-4o-transcribe)
    
    Args:
        audio_path (str): Ruta al archivo de audio
        api_key (str): Clave API de OpenAI
        
    Returns:
        str or None: Texto transcrito o None si hay error
    """
    try:
        logger.info(f"Transcribiendo audio con modelo {OPENAI_STT_MODEL}")
        headers = {"Authorization": f"Bearer {api_key}"}
        
        with open(audio_path, "rb") as audio_file:
            files = {
                "file": (os.path.basename(audio_path), audio_file, "audio/wav"),
                "model": (None, OPENAI_STT_MODEL)
            }
            
            logger.debug("Enviando solicitud de transcripción")
            start_time = time.time()
            response = requests.post(OPENAI_TRANSCRIBE_URL, headers=headers, files=files)
            request_time = time.time() - start_time
            logger.info(f"Transcripción completada en {request_time:.2f} segundos")
            
            if response.status_code == 200:
                result = response.json()
                transcript = result.get("text", "")
                logger.info(f"Texto transcrito: {transcript[:100]}...")
                return transcript
            else:
                logger.error(f"Error en la transcripción: {response.status_code} - {response.text[:200]}")
                return None
                
    except Exception as e:
        logger.error(f"Error en transcripción: {e}")
        logger.error(traceback.format_exc())
        return None

def text_to_speech(text, api_key, voice=None, instructions=None):
    """
    Convierte texto a voz usando la API de OpenAI (gpt-4o-mini-tts)
    
    Args:
        text (str): Texto a convertir en voz
        api_key (str): Clave API de OpenAI
        voice (str, optional): Voz a utilizar. Por defecto usa la configurada en config.py
        instructions (str, optional): Instrucciones adicionales para la síntesis de voz
        
    Returns:
        bytes or None: Audio generado como bytes o None si hay error
    """
    try:
        if not voice:
            voice = OPENAI_TTS_VOICE
            
        logger.info(f"Generando voz con modelo {OPENAI_TTS_MODEL}, voz {voice}")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": OPENAI_TTS_MODEL,
            "input": text,
            "voice": voice,
            "response_format": OPENAI_TTS_FORMAT
        }
        
        if instructions:
            payload["instructions"] = instructions
            
        logger.debug(f"Payload para TTS: {json.dumps(payload)[:200]}...")
        
        start_time = time.time()
        response = requests.post(OPENAI_SPEECH_URL, headers=headers, json=payload)
        request_time = time.time() - start_time
        logger.info(f"Síntesis de voz completada en {request_time:.2f} segundos")
        
        if response.status_code == 200:
            logger.info(f"Audio generado correctamente: {len(response.content)} bytes")
            return response.content
        else:
            logger.error(f"Error en la síntesis de voz: {response.status_code} - {response.text[:200]}")
            return None
            
    except Exception as e:
        logger.error(f"Error en síntesis de voz: {e}")
        logger.error(traceback.format_exc())
        return None