import os
import json
import time
import openai
import pyaudio
import wave
import numpy as np
import subprocess
import sys
from pydub import AudioSegment
from pydub.playback import play
from dotenv import load_dotenv
from pathlib import Path

# Cargar variables de entorno
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Configuración de Audio
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Whisper funciona mejor con 16kHz
CHUNK = 1024
SILENCE_THRESHOLD = 200  # Ajustar si es necesario
MAX_SILENCE_CHUNKS = 30  # Segundos de silencio antes de cortar

# Inicializar PyAudio
p = pyaudio.PyAudio()

# Historial de conversación en la sesión activa
conversation_history = []

# Ruta del script de FAISS
script_path = os.path.join(os.path.dirname(__file__), "embeddings", "buscar_pregunta.py")


def record_audio(filename="temp_user.wav"):
    """Graba audio del micrófono y lo guarda en un archivo"""
    print("Esperando voz... (Habla para comenzar)")
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    frames = []
    silent_chunks = 0
    speaking = False

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

        # Convertir a numpy array para análisis
        audio_data = np.frombuffer(data, dtype=np.int16)
        amplitude = np.max(np.abs(audio_data))

        if amplitude > SILENCE_THRESHOLD:
            speaking = True
            silent_chunks = 0  # Reiniciar el contador de silencio
        elif speaking:
            silent_chunks += 1

        if silent_chunks > MAX_SILENCE_CHUNKS:  # Corta después de demasiado silencio
            print("Silencio detectado. Terminando grabación...")
            break

    stream.stop_stream()
    stream.close()

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))

    print("Audio guardado.")


def transcribe_audio(filename):
    """Convierte el audio grabado a texto con Whisper"""
    with open(filename, "rb") as audio_file:
        resp = openai.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return resp.text.strip() if resp.text else None


def search_faiss(query):
    """Ejecuta FAISS para buscar una respuesta en la base de datos"""
    try:
        venv_python = sys.executable  # Python dentro del venv
        faiss_script = os.path.join(os.path.dirname(__file__), "embeddings", "buscar_pregunta.py")

        print(f"Ejecutando FAISS en: {faiss_script}")
        print(f"Buscando: {query}")

        result = subprocess.run(
            [venv_python, "-u", faiss_script, query],  
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
            text=True, encoding="utf-8", errors="ignore"
        )

        response = result.stdout.strip()
        error_output = result.stderr.strip()

        if error_output:
            print(f"Error en FAISS: {error_output}")
            return None

        if not response or "Lo siento" in response or "Error" in response:
            print("FAISS no encontró coincidencias. Se usará GPT sin contexto.")
            return None

        return response

    except Exception as e:
        print(f"Error en búsqueda FAISS: {str(e)}")
        return None


def ask_gpt(contexto, user_input):
    """Usa GPT para responder si FAISS no encuentra una coincidencia"""
    messages = [
        {
            "role": "system",
            "content": (
                "Eres un asistente de soporte basado en preguntas frecuentes. "
                "Solo puedes responder con información que se encuentre en la base de datos. "
                "Si no encuentras una respuesta, responde 'No tengo información sobre eso'."
            )
        }
    ]

    messages.extend(conversation_history[-5:])

    if contexto:
        messages.append({"role": "system", "content": f"Información relevante: {contexto}"})

    messages.append({"role": "user", "content": user_input})

    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    conversation_history.append({"role": "user", "content": user_input})
    conversation_history.append({"role": "assistant", "content": response.choices[0].message.content})

    return response.choices[0].message.content


def text_to_speech(text, filename="temp_assistant.mp3"):
    """Convierte texto a voz usando OpenAI TTS"""
    speech_file_path = Path(filename)

    response = openai.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text
    )

    speech_file_path.write_bytes(response.content)
    return str(speech_file_path)


def play_audio(filename):
    """Reproduce un archivo de audio"""
    try:
        audio = AudioSegment.from_file(filename, format="mp3")
        play(audio)
    except Exception as e:
        print(f"Error al reproducir el audio: {e}")


def main_pipeline():
    """Ejecuta todo el pipeline de STT -> FAISS/GPT -> TTS"""
    print("\n=== DEMO PIPELINE MANUAL: STT -> RAG -> GPT -> TTS ===\n")
    print("Habla directamente. El sistema detectará automáticamente tu voz.\n")

    while True:
        record_audio()
        user_text = transcribe_audio("temp_user.wav")

        if not user_text:
            print("No se detectó voz o el audio estaba vacío. Intentando de nuevo...")
            continue

        print(f"Usuario: {user_text}")

        contexto = search_faiss(user_text)

        if contexto:
            response_text = contexto
        else:
            response_text = ask_gpt(contexto, user_text)

        audio_file = text_to_speech(response_text)
        play_audio(audio_file)


if __name__ == "__main__":
    main_pipeline()
