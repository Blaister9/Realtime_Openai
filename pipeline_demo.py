import os
import json
import time
import openai
import pyaudio
import wave
import numpy as np
import subprocess
from pydub import AudioSegment
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# 🎤 Configuración de Audio
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000  # Whisper funciona mejor con 16kHz
CHUNK = 1024
SILENCE_THRESHOLD = 1000  # Ajustar si es necesario
MAX_SILENCE_CHUNKS = 30  # Segundos de silencio antes de cortar
MODEL = "gpt-4o-mini"  # Modelo más barato y rápido
MAX_TOKENS = 200  # Limitar tamaño de respuesta
MAX_HISTORY = 3  # Historial de conversación
MODEL_TTS = "tts-1"
VOICE_TTS = "nova"
WHISPER_MODEL = "whisper-1"
MAX_FILE_SIZE_MB = 25  # Límite de OpenAI para archivos de audio
RETRY_LIMIT = 3  # Reintentos en caso de fallo
CHUNK_SIZE = 1024
MAX_HISTORY_TOKENS = 1024  # Máximo de tokens en el historial

conversation_history = []  # Historial de la conversación
tts_cache = {}  # Cache para evitar generar TTS repetidamente

# 🔄 Inicializar PyAudio
p = pyaudio.PyAudio()

# 🎤 Grabación automática con detección de voz
def record_audio(filename="temp_user.wav"):
    print("🎤 Esperando voz... (Habla para comenzar)")
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    
    frames = []
    silent_chunks = 0
    speaking = False

    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)
        audio_data = np.frombuffer(data, dtype=np.int16)
        amplitude = np.max(np.abs(audio_data))

        if amplitude > SILENCE_THRESHOLD:
            speaking = True
            silent_chunks = 0
        elif speaking:
            silent_chunks += 1

        if silent_chunks > MAX_SILENCE_CHUNKS:
            print("🔇 Silencio detectado. Terminando grabación...")
            break

    stream.stop_stream()
    stream.close()

    with wave.open(filename, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b"".join(frames))

    print(f"🔹 Audio guardado en '{filename}'.")

# 📌 Convertir a formato compatible con OpenAI
def convert_audio_to_mp3(input_file, output_file="temp_user.mp3"):
    audio = AudioSegment.from_wav(input_file)
    audio.export(output_file, format="mp3")
    return output_file

# 📝 Transcripción de audio con Whisper API
def transcribe_audio(filename):
    mp3_filename = convert_audio_to_mp3(filename)
    
    retries = 0
    while retries < RETRY_LIMIT:
        try:
            with open(mp3_filename, "rb") as f:
                response = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=f,
                    response_format="text",
                    prompt="Este es un asistente virtual que responde preguntas sobre horarios, soporte y citas."
                )
            return response.strip()
        except Exception as e:
            print(f"⚠️ Error en transcripción ({retries+1}/{RETRY_LIMIT}): {e}")
            retries += 1

    return "⚠️ No se pudo transcribir el audio."

# 🔍 Buscar en FAISS usando `buscar_pregunta.py`
def search_faiss(query):
    try:
        result = subprocess.run(
            ["python", "embeddings/buscar_pregunta.py", query],
            capture_output=True, text=True
        )
        response = result.stdout.strip()
        return response if "Error" not in response else None
    except Exception as e:
        return None

# 🤖 Generar respuesta con GPT
def ask_gpt(contexto, user_input):
    global conversation_history
    messages = [{"role": "system", "content": "Responde solo con información de la base de datos. Si no hay respuesta, di 'No lo sé'."}]
    
    conversation_history = conversation_history[-MAX_HISTORY:]
    messages.extend(conversation_history)

    if contexto:
        messages.append({"role": "system", "content": f"Información relevante: {contexto}"})

    messages.append({"role": "user", "content": user_input})

    try:
        response = openai.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            response_format="json"
        )
        respuesta = response.choices[0].message.content.strip()
        conversation_history.append({"role": "user", "content": user_input})
        conversation_history.append({"role": "assistant", "content": respuesta})
        return respuesta
    except Exception as e:
        return "Lo siento, ocurrió un error."

# 🎶 Convertir texto en voz con OpenAI TTS
def text_to_speech(text):
    if len(text) > 200:
        text = text[:200] + "..."
    
    if text in tts_cache:
        return tts_cache[text]

    response = openai.audio.speech.create(
        model=MODEL_TTS,
        voice=VOICE_TTS,
        input=text,
        response_format="mp3"
    )

    tts_cache[text] = response
    return response

# 🎧 Reproducir audio
def play_audio(response):
    filename = "temp_response.mp3"
    with open(filename, "wb") as f:
        f.write(response.content)

    os.system(f"start {filename}")

# 🎯 **Pipeline Principal**
def main_pipeline():
    print("\n=== DEMO PIPELINE MANUAL: STT -> RAG -> GPT -> TTS ===\n")
    print("Habla directamente. El sistema detectará automáticamente tu voz.\n")

    while True:
        print("\n🎤 Esperando voz...")
        record_audio()  # Capturar audio

        user_text = transcribe_audio("temp_user.wav")  # Transcribir STT
        if not user_text:
            print("⚠️ No se detectó voz o el audio estaba vacío.")
            continue

        print(f"👤 Usuario: {user_text}")

        contexto = search_faiss(user_text)

        response_text = contexto if contexto else ask_gpt(contexto, user_text)
        print(f"🤖 Asistente: {response_text}")

        audio_response = text_to_speech(response_text)
        play_audio(audio_response)

if __name__ == "__main__":
    main_pipeline()
