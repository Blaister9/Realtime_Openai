import os
import json
import time
import openai
import pyaudio
import wave
import numpy as np
import sys
from dotenv import load_dotenv
from embeddings.buscar_pregunta import faiss_search
from openai import OpenAI

# Cargar variables de entorno
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Configuración de Audio
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Whisper funciona mejor con 16kHz
CHUNK = 1024
SILENCE_THRESHOLD = 300  # Incrementado de 200
MAX_SILENCE_CHUNKS = 15   # Reducido de 30
PRE_RECORD_BUFFER = 5     # Chunks de buffer inicial

# Inicializar PyAudio
p = pyaudio.PyAudio()

# Historial de conversación
conversation_history = []
CACHE_TTS = {}  # Cache para respuestas frecuentes

def record_audio(filename="temp_user.wav"):
    """Graba audio optimizado con buffer previo"""
    start_time = time.time()
    print("\nEsperando voz... (Habla para comenzar)")
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    frames = []
    buffer = [stream.read(CHUNK) for _ in range(PRE_RECORD_BUFFER)]
    silent_chunks = 0
    speaking = False

    while True:
        data = buffer.pop(0) if buffer else stream.read(CHUNK)
        frames.append(data)

        # Análisis de amplitud optimizado
        amplitude = np.frombuffer(data, dtype=np.int16).max()
        
        if not speaking and amplitude > SILENCE_THRESHOLD:
            speaking = True
            silent_chunks = 0
            # Recuperar buffer previo al hablar
            frames = buffer[-PRE_RECORD_BUFFER:] + frames

        if speaking:
            if amplitude <= SILENCE_THRESHOLD:
                silent_chunks += 1
            else:
                silent_chunks = 0

            if silent_chunks > MAX_SILENCE_CHUNKS:
                break

    stream.stop_stream()
    stream.close()

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))

    print(f"Audio guardado. Tiempo: {time.time() - start_time:.2f}s")

def transcribe_audio(filename):
    """Convierte el audio grabado a texto con Whisper"""
    start_time = time.time()
    try:
        with open(filename, "rb") as audio_file:
            resp = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
            transcription = resp.text.strip() if resp.text else None
            print(f"Tiempo STT (Whisper): {time.time() - start_time:.2f}s")
            return transcription
    except Exception as e:
        print(f"Error en STT: {str(e)}")
        return None

def search_faiss(query):
    """Búsqueda optimizada en FAISS"""
    start_time = time.time()
    try:
        respuesta = faiss_search(query)
        print(f"Tiempo FAISS optimizado: {time.time() - start_time:.2f}s")
        return respuesta
    except Exception as e:
        print(f"Error en FAISS: {str(e)}")
        return None

def ask_gpt(contexto, user_input):
    """Generación de respuesta con GPT-4"""
    start_time = time.time()
    messages = [
        {
            "role": "system",
            "content": (
                "Eres un asistente de soporte especializado en preguntas frecuentes. Solo responde en español. Fuiste creado por la ANDJE "
                "Respuesta concisa y precisa basada solo en la base de datos. "
                "Si no hay información relevante, di 'No tengo información sobre eso'."
            )
        }
    ]
    
    # Mantener último contexto de conversación
    messages.extend(conversation_history[-2:])  # Reducido a 2 mensajes anteriores
    
    if contexto:
        messages.append({"role": "system", "content": f"Contexto relevante: {contexto}"})

    messages.append({"role": "user", "content": user_input})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Modelo más rápido
            messages=messages,
            max_tokens=300  # Limitar longitud de respuesta
        )
        respuesta = response.choices[0].message.content
        
        # Actualizar historial
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": respuesta})
        
        print(f"Tiempo GPT: {time.time() - start_time:.2f}s")
        return respuesta
    except Exception as e:
        print(f"Error en GPT: {str(e)}")
        return "Lo siento, hubo un error al generar la respuesta."

def text_to_speech_stream(text):
    """Generación de audio con caché y parámetros corregidos"""
    if text in CACHE_TTS:
        print("[CACHE] Respuesta usada")
        return CACHE_TTS[text]

    start_time = time.time()
    try:
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            input=text,
            response_format="pcm",
            speed=1.2
        )
        CACHE_TTS[text] = response
        print(f"Tiempo TTS: {time.time() - start_time:.2f}s")
        return response
    except Exception as e:
        print(f"Error TTS: {str(e)}")
        return None

def play_streaming_audio(response):
    """Reproducción mejorada con manejo de tiempo real"""
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=24000,
        output=True
    )

    chunk_size = 4096
    max_duration = 30  # Segundos máximos de reproducción
    start_time = time.time()
    first_chunk = True

    try:
        for chunk in response.iter_bytes(chunk_size):
            if time.time() - start_time > max_duration:
                print("\nInterrupción por tiempo máximo")
                break
            
            if first_chunk:
                print(f"Primer chunk: {time.time() - start_time:.2f}s")
                first_chunk = False
            
            stream.write(chunk)
        
        print(f"Duración total: {time.time() - start_time:.2f}s")
    except Exception as e:
        print(f"Error reproducción: {str(e)}")
    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

def main_pipeline():
    print("\n=== PIPELINE OPTIMIZADO CON STREAMING EN TIEMPO REAL ===\n")
    
    while True:
        ciclo_start = time.time()
        
        # 1. Grabación de audio
        record_audio()
        
        # 2. Transcripción a texto
        stt_start = time.time()
        user_text = transcribe_audio("temp_user.wav")
        if not user_text:
            continue
        print(f"[TIMING] STT Total: {time.time() - stt_start:.2f}s")
        print(f"Usuario: {user_text}")
        
        # 3. Búsqueda en FAISS
        rag_start = time.time()
        contexto = search_faiss(user_text)
        print(f"[TIMING] FAISS Total: {time.time() - rag_start:.2f}s")
        
        # 4. Generación de respuesta
        if not contexto:
            gpt_start = time.time()
            response_text = ask_gpt(contexto, user_text)
            print(f"[TIMING] GPT Total: {time.time() - gpt_start:.2f}s")
        else:
            response_text = contexto
        
        # 5. Generación y reproducción de audio
        tts_start = time.time()
        tts_response = text_to_speech_stream(response_text)
        if tts_response:
            play_streaming_audio(tts_response)
        print(f"[TIMING] TTS Total: {time.time() - tts_start:.2f}s")
        
        # 6. Estadísticas finales
        print(f"\n[TIMING] Ciclo completo: {time.time() - ciclo_start:.2f}s")
        print("="*50 + "\n")

if __name__ == "__main__":
    main_pipeline()