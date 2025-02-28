import json
import base64
import time
import wave
import threading
import sys

import pyaudio
import websocket

from embeddings.buscar_pregunta import faiss_search

# ---------------------------
# CONFIGURACIÓN DE LA API
# ---------------------------
API_KEY = os.environ.get("OPENAI_API_KEY")
REALTIME_MODEL = "gpt-4o-realtime-preview-2024-12-17"
REALTIME_URL = f"wss://api.openai.com/v1/realtime?model={REALTIME_MODEL}"

HEADERS_DICT = {
    "Authorization": f"Bearer {API_KEY}",
    "OpenAI-Beta": "realtime=v1"
}

# ---------------------------
# CONFIGURACIÓN DE AUDIO
# ---------------------------
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
NUM_CHANNELS = 1
FORMAT = pyaudio.paInt16  # PCM16

# ---------------------------
# BÚSQUEDA EN FAISS
# ---------------------------
def get_faq_answer(question: str):
    """Llama a la búsqueda semántica con embeddings en FAISS."""
    answer = faiss_search(question, threshold=0.5)
    return answer

# ---------------------------
# VARIABLES GLOBALES
# ---------------------------
p = pyaudio.PyAudio()
audio_output_stream = None
audio_input_stream = None

lock_audio_output = threading.Lock()

# --- BARGE-IN FLAGS ---
in_response = False
barge_in = False
current_response_id = None

# Indica si cerramos voluntariamente la conexión (p.e. Ctrl+C) o no.
graceful_shutdown = False

def on_message(ws, message):
    global in_response, barge_in, current_response_id

    event = json.loads(message)
    event_type = event.get("type", "")

    if event_type == "session.created":
        print("[INFO] Sesión Realtime creada con éxito.")

    elif event_type == "session.updated":
        print("[INFO] Sesión actualizada.")

    elif event_type == "response.created":
        current_response_id = event["response"]["id"]
        in_response = True
        barge_in = False

    elif event_type == "response.done":
        current_response_id = None
        in_response = False
        barge_in = False

    elif event_type == "input_audio_buffer.speech_started":
        print("[VAD] Comenzó a detectar voz.")

    elif event_type == "input_audio_buffer.speech_stopped":
        print("[VAD] Terminó de detectar voz.")

    elif event_type == "response.text.delta":
        partial_text = event["delta"]
        sys.stdout.write(f"\r[Parcial] {partial_text}   ")
        sys.stdout.flush()

    elif event_type == "response.text.done":
        final_text = event["response"]["output"][0]["text"]
        print(f"\n[Transcripción final]: {final_text}")

    elif event_type == "response.audio.delta":
        # Chunks de audio TTS
        if barge_in:
            # Si ya cancelamos, ignoramos lo que sigue
            return

        audio_chunk_b64 = event["delta"]
        audio_chunk = base64.b64decode(audio_chunk_b64)
        with lock_audio_output:
            if audio_output_stream is not None:
                audio_output_stream.write(audio_chunk)

    elif event_type == "response.audio.done":
        print("[INFO] Fin del audio TTS.")

    elif event_type == "error":
        err_msg = event.get("error",{}).get("message","")
        if "Cancellation failed: no active response found" in err_msg:
            print("[DEBUG] No había respuesta activa para cancelar; ignorando.")
        else:
            print("[ERROR]", event)

    elif event_type == "response.function_call_arguments.done":
        call_id = event["call_id"]
        args_json_str = event["arguments"]
        print(f"\n[FUNC_CALL] El modelo está llamando a la función con args={args_json_str}")
        try:
            args = json.loads(args_json_str)
            question = args.get("question", "")
            answer = get_faq_answer(question)
            if not answer:
                answer = "Lo siento, no encontré esa respuesta en mi base de datos."

            send_function_call_output(ws, call_id, answer)

        except Exception as e:
            print("[ERROR parseando args de function call]", e)

def on_error(ws, error):
    print("[on_error]", error)

def on_close(ws, close_status_code, close_msg):
    global graceful_shutdown
    print("[on_close] Conexión cerrada:", close_status_code, close_msg)
    stop_audio_streams()

    # Si NO fue un cierre voluntario, lanzamos una excepción
    # para que se reintente conexión
    if not graceful_shutdown:
        raise ConnectionError("Conexión finalizada inesperadamente")

def on_open(ws):
    print("[on_open] Conectado a la Realtime API.")
    # Cambia la voz e instrucciones
    session_update = {
        "type": "session.update",
        "session": {
            "voice": "ash",
            "instructions": (
                "Eres un asistente de voz. Habla con voz suave y tranquilizadora. "
                "Siempre llama a la función get_faq_answer si el usuario pide datos que puedan estar "
                "en la base de FAQs. De lo contrario, respóndele directamente en español. "
                "Habla de forma amable y concisa."
            ),
            "turn_detection": {
                "type": "server_vad",
                "threshold": 0.4,
                "prefix_padding_ms": 300,
                "silence_duration_ms": 200,
                "create_response": True,
                "interrupt_response": True
            },
            "tools": [
                {
                    "type": "function",
                    "name": "get_faq_answer",
                    "description": "Obtiene una respuesta de las FAQs internas si aplica.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "Pregunta del usuario en texto."
                            }
                        },
                        "required": ["question"]
                    }
                }
            ],
            "tool_choice": "auto",
            "modalities": ["audio", "text"],
            "max_response_output_tokens": 200
        }
    }
    ws.send(json.dumps(session_update))


# ---------------------------
# Funciones auxiliares
# ---------------------------

def capture_microphone():
    global audio_input_stream

    audio_input_stream = p.open(
        format=FORMAT,
        channels=NUM_CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK_SIZE
    )

    while True:
        try:
            audio_data = audio_input_stream.read(CHUNK_SIZE, exception_on_overflow=False)
            b64_chunk = base64.b64encode(audio_data).decode('utf-8')
            input_audio_event = {
                "type": "input_audio_buffer.append",
                "audio": b64_chunk
            }
            ws.send(json.dumps(input_audio_event))
        except Exception as e:
            print("[AudioCaptureError]", e)
            break

    if audio_input_stream:
        audio_input_stream.close()
        audio_input_stream = None

def start_audio_output_stream():
    global audio_output_stream
    audio_output_stream = p.open(
        format=FORMAT,
        channels=NUM_CHANNELS,
        rate=SAMPLE_RATE,
        output=True,
        frames_per_buffer=CHUNK_SIZE
    )
    return audio_output_stream

def stop_audio_streams():
    global audio_input_stream, audio_output_stream
    with lock_audio_output:
        if audio_output_stream is not None:
            audio_output_stream.stop_stream()
            audio_output_stream.close()
            audio_output_stream = None
    if audio_input_stream is not None:
        audio_input_stream.stop_stream()
        audio_input_stream.close()
        audio_input_stream = None

def send_function_call_output(ws, call_id, function_result):
    output_item_event = {
        "type": "conversation.item.create",
        "item": {
            "type": "function_call_output",
            "call_id": call_id,
            "output": json.dumps({"faq_answer": function_result}, ensure_ascii=False)
        }
    }
    ws.send(json.dumps(output_item_event))

    resp_event = {
        "type": "response.create",
        "response": {
            "modalities": ["audio", "text"]
        }
    }
    ws.send(json.dumps(resp_event))

# ---------------------------
# run_realtime
# ---------------------------
def run_realtime():
    """
    Esta función se encarga de:
      1) Conectarse al WS.
      2) Iniciar audio input y output.
      3) Esperar hasta desconexión o Ctrl+C.
    """
    global ws, graceful_shutdown

    headers_list = [f"{k}: {v}" for k, v in HEADERS_DICT.items()]

    ws = websocket.WebSocketApp(
        REALTIME_URL,
        header=headers_list,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    # Ajustas ping_interval y ping_timeout (por defecto None)
    ws_thread = threading.Thread(target=lambda: ws.run_forever(ping_interval=None, ping_timeout=120), daemon=True)
    ws_thread.start()

    # Esperamos un rato a que se establezca la conexión
    time.sleep(10)
    if ws.sock and ws.sock.connected:
        print("[MAIN] WebSocket conectado. Iniciando audio.")
        start_audio_output_stream()
        capture_thread = threading.Thread(target=capture_microphone, daemon=True)
        capture_thread.start()
        print("[MAIN] Presiona Ctrl+C para terminar.")
        try:
            while True:
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("[MAIN] Finalizando por Ctrl+C...")
        finally:
            graceful_shutdown = True
            ws.close()
            stop_audio_streams()
            time.sleep(1.0)
    else:
        print("[ERROR] No se pudo conectar al WebSocket. Saliendo.")
        raise ConnectionError("No se pudo conectar al WebSocket.")


# ---------------------------
# MAIN LOOP con reintentos
# ---------------------------
def main():
    global graceful_shutdown
    while True:
        try:
            graceful_shutdown = False
            run_realtime()
            # Si la ejecución termina sin excepción, salimos del while
            print("[MAIN] run_realtime finalizó normalmente.")
            break
        except ConnectionError as ce:
            # Reconexión en 5 segundos
            print(f"[MAIN] Se perdió la conexión: {ce}")
            time.sleep(5)
            print("[MAIN] Reintentando conexión...")
            continue
        except KeyboardInterrupt:
            print("[MAIN] Salida por Ctrl+C detectada en el loop principal.")
            break
        except Exception as e:
            print(f"[MAIN] Error no controlado: {e}")
            time.sleep(5)
            print("[MAIN] Reintentando conexión...")
            continue


if __name__ == "__main__":
    main()
