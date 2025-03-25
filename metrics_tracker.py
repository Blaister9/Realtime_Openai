#!/usr/bin/env python3
import os
import json
import time
import datetime
import logging
import csv
from pathlib import Path

logger = logging.getLogger(__name__)

class CallMetrics:
    """Clase para registrar y analizar métricas de cada llamada al asistente virtual"""
    
    def __init__(self, base_dir, call_id=None):
        """
        Inicializa el tracker de métricas
        
        Args:
            base_dir (str): Directorio base para guardar métricas
            call_id (str, optional): Identificador único de la llamada. Si es None, se genera automáticamente
        """
        self.base_dir = base_dir
        self.metrics_dir = os.path.join(base_dir, "metrics")
        self.transcripts_dir = os.path.join(base_dir, "transcripts")
        
        # Crear directorios si no existen
        os.makedirs(self.metrics_dir, exist_ok=True)
        os.makedirs(self.transcripts_dir, exist_ok=True)
        
        # Generar ID de llamada si no se proporciona
        if call_id is None:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.call_id = f"call_{timestamp}"
        else:
            self.call_id = call_id
            
        # Inicializar diccionario de métricas
        self.metrics = {
            "call_id": self.call_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "duration": {
                "total": 0,
                "stt": 0,
                "llm": 0,
                "tts": 0,
                "faiss": 0
            },
            "tokens": {
                "input": 0,
                "output": 0,
                "total": 0
            },
            "costs": {
                "stt": 0,
                "llm": 0,
                "tts": 0,
                "total": 0
            },
            "audio": {
                "input_size_bytes": 0,
                "output_size_bytes": 0,
                "input_duration_seconds": 0,
                "output_duration_seconds": 0
            },
            "models": {
                "stt": "",
                "llm": "",
                "tts": ""
            },
            "status": {
                "stt_success": False,
                "llm_success": False,
                "tts_success": False,
                "overall_success": False
            },
            "faiss": {
                "used": False,
                "found_answer": False
            }
        }
        
        # Inicializar transcripciones
        self.transcripts = {
            "user_input": "",
            "assistant_response": "",
            "faiss_response": ""
        }
        
        # Inicializar tiempos
        self.start_time = time.time()
        self.step_start_time = None
        
    def start_step(self, step_name):
        """
        Marca el inicio de un paso del proceso
        
        Args:
            step_name (str): Nombre del paso (stt, llm, tts, faiss)
        """
        self.step_start_time = time.time()
        logger.debug(f"Inicio de paso: {step_name}")
        
    def end_step(self, step_name):
        """
        Marca el fin de un paso y registra su duración
        
        Args:
            step_name (str): Nombre del paso (stt, llm, tts, faiss)
            
        Returns:
            float: Duración del paso en segundos
        """
        if self.step_start_time is None:
            logger.warning(f"Se intentó finalizar el paso {step_name} sin haberlo iniciado")
            return 0
            
        duration = time.time() - self.step_start_time
        self.metrics["duration"][step_name] = round(duration, 3)
        logger.debug(f"Fin de paso {step_name}: {duration:.3f} segundos")
        
        return duration
        
    def set_transcript(self, user_input=None, assistant_response=None, faiss_response=None):
        """
        Establece las transcripciones de la conversación
        
        Args:
            user_input (str, optional): Entrada transcrita del usuario
            assistant_response (str, optional): Respuesta del asistente
            faiss_response (str, optional): Respuesta de FAISS
        """
        if user_input is not None:
            self.transcripts["user_input"] = user_input
            
        if assistant_response is not None:
            self.transcripts["assistant_response"] = assistant_response
            
        if faiss_response is not None:
            self.transcripts["faiss_response"] = faiss_response
            
    def set_token_usage(self, input_tokens, output_tokens):
        """
        Establece el uso de tokens del LLM
        
        Args:
            input_tokens (int): Tokens de entrada
            output_tokens (int): Tokens de salida
        """
        self.metrics["tokens"]["input"] = input_tokens
        self.metrics["tokens"]["output"] = output_tokens
        self.metrics["tokens"]["total"] = input_tokens + output_tokens
        
    def set_costs(self, stt_cost=0, llm_cost=0, tts_cost=0):
        """
        Establece los costos de la llamada
        
        Args:
            stt_cost (float): Costo de transcripción
            llm_cost (float): Costo del LLM
            tts_cost (float): Costo de síntesis de voz
        """
        self.metrics["costs"]["stt"] = round(stt_cost, 6)
        self.metrics["costs"]["llm"] = round(llm_cost, 6)
        self.metrics["costs"]["tts"] = round(tts_cost, 6)
        self.metrics["costs"]["total"] = round(stt_cost + llm_cost + tts_cost, 6)
        
    def set_audio_metrics(self, input_size=0, output_size=0, input_duration=0, output_duration=0):
        """
        Establece métricas relacionadas con el audio
        
        Args:
            input_size (int): Tamaño del audio de entrada en bytes
            output_size (int): Tamaño del audio de salida en bytes
            input_duration (float): Duración del audio de entrada en segundos
            output_duration (float): Duración del audio de salida en segundos
        """
        self.metrics["audio"]["input_size_bytes"] = input_size
        self.metrics["audio"]["output_size_bytes"] = output_size
        self.metrics["audio"]["input_duration_seconds"] = input_duration
        self.metrics["audio"]["output_duration_seconds"] = output_duration
        
    def set_models(self, stt_model="", llm_model="", tts_model=""):
        """
        Establece los modelos utilizados
        
        Args:
            stt_model (str): Modelo de STT
            llm_model (str): Modelo de LLM
            tts_model (str): Modelo de TTS
        """
        self.metrics["models"]["stt"] = stt_model
        self.metrics["models"]["llm"] = llm_model
        self.metrics["models"]["tts"] = tts_model
        
    def set_status(self, stt_success=False, llm_success=False, tts_success=False):
        """
        Establece el estado de éxito de cada paso
        
        Args:
            stt_success (bool): Si la transcripción fue exitosa
            llm_success (bool): Si la llamada al LLM fue exitosa
            tts_success (bool): Si la síntesis de voz fue exitosa
        """
        self.metrics["status"]["stt_success"] = stt_success
        self.metrics["status"]["llm_success"] = llm_success
        self.metrics["status"]["tts_success"] = tts_success
        self.metrics["status"]["overall_success"] = stt_success and llm_success and tts_success
        
    def set_faiss_metrics(self, used=False, found_answer=False):
        """
        Establece métricas relacionadas con FAISS
        
        Args:
            used (bool): Si se utilizó FAISS
            found_answer (bool): Si FAISS encontró una respuesta
        """
        self.metrics["faiss"]["used"] = used
        self.metrics["faiss"]["found_answer"] = found_answer
        
    def calculate_costs(self):
        """
        Calcula los costos basados en el uso y los modelos utilizados
        
        Note:
            Precios aproximados actualizados hasta Marzo 2024, ajustar según cambios de OpenAI
        """
        # Precios por 1000 tokens en USD (aproximados)
        STT_PRICE_PER_MINUTE = {
            "gpt-4o-transcribe": 0.006,  # $0.006 por minuto
            "gpt-4o-mini-transcribe": 0.003  # $0.003 por minuto
        }
        
        LLM_PRICE_PER_1K = {
            "gpt-4o": {
                "input": 0.01,  # $0.01 por 1000 tokens de entrada
                "output": 0.03  # $0.03 por 1000 tokens de salida
            },
            "gpt-4o-mini": {
                "input": 0.00175,  # $0.00175 por 1000 tokens de entrada
                "output": 0.00525  # $0.00525 por 1000 tokens de salida
            }
        }
        
        TTS_PRICE_PER_1K = {
            "gpt-4o-mini-tts": 0.004  # $0.004 por 1000 caracteres
        }
        
        # Calcular costo de STT
        stt_model = self.metrics["models"]["stt"]
        input_duration_minutes = self.metrics["audio"]["input_duration_seconds"] / 60
        if stt_model in STT_PRICE_PER_MINUTE:
            stt_cost = input_duration_minutes * STT_PRICE_PER_MINUTE[stt_model]
        else:
            stt_cost = 0
            
        # Calcular costo de LLM
        llm_model = self.metrics["models"]["llm"]
        if llm_model in LLM_PRICE_PER_1K:
            input_tokens = self.metrics["tokens"]["input"]
            output_tokens = self.metrics["tokens"]["output"]
            input_cost = (input_tokens / 1000) * LLM_PRICE_PER_1K[llm_model]["input"]
            output_cost = (output_tokens / 1000) * LLM_PRICE_PER_1K[llm_model]["output"]
            llm_cost = input_cost + output_cost
        else:
            llm_cost = 0
            
        # Calcular costo de TTS
        tts_model = self.metrics["models"]["tts"]
        if tts_model in TTS_PRICE_PER_1K:
            response_chars = len(self.transcripts["assistant_response"])
            tts_cost = (response_chars / 1000) * TTS_PRICE_PER_1K[tts_model]
        else:
            tts_cost = 0
            
        # Establecer costos
        self.set_costs(stt_cost, llm_cost, tts_cost)
        
    def finalize(self):
        """
        Finaliza el registro de métricas, calcula la duración total y guarda los archivos
        
        Returns:
            dict: Métricas finales
        """
        # Calcular duración total
        total_duration = time.time() - self.start_time
        self.metrics["duration"]["total"] = round(total_duration, 3)
        
        # Calcular costos basados en uso
        self.calculate_costs()
        
        # Guardar transcripciones
        self._save_transcripts()
        
        # Guardar métricas en JSON
        self._save_metrics_json()
        
        # Añadir registro al CSV acumulativo
        self._append_to_csv()
        
        return self.metrics
        
    def _save_transcripts(self):
        """Guarda las transcripciones en archivos de texto"""
        transcript_file = os.path.join(self.transcripts_dir, f"{self.call_id}.txt")
        
        with open(transcript_file, "w", encoding="utf-8") as f:
            f.write(f"LLAMADA: {self.call_id}\n")
            f.write(f"FECHA: {self.metrics['timestamp']}\n")
            f.write("="*50 + "\n\n")
            
            f.write("USUARIO:\n")
            f.write(self.transcripts["user_input"] + "\n\n")
            
            if self.transcripts["faiss_response"]:
                f.write("RESPUESTA FAISS:\n")
                f.write(self.transcripts["faiss_response"] + "\n\n")
                
            f.write("ASISTENTE:\n")
            f.write(self.transcripts["assistant_response"] + "\n\n")
            
            f.write("="*50 + "\n")
            f.write(f"Duración total: {self.metrics['duration']['total']:.3f} segundos\n")
        
        logger.info(f"Transcripciones guardadas en {transcript_file}")
        
    def _save_metrics_json(self):
        """Guarda las métricas en formato JSON"""
        try:
            metrics_file = os.path.join(self.metrics_dir, f"{self.call_id}.json")
            
            with open(metrics_file, "w", encoding="utf-8") as f:
                json.dump(self.metrics, f, indent=2)
                
            logger.info(f"Métricas guardadas en {metrics_file}")
        except Exception as e:
            logger.error(f"Error guardando métricas JSON: {e}")
            logger.error(traceback.format_exc())
        
    def _append_to_csv(self):
        """Añade las métricas a un archivo CSV acumulativo"""
        csv_file = os.path.join(self.metrics_dir, "call_metrics.csv")
        file_exists = os.path.isfile(csv_file)
        
        # Preparar datos para CSV (estructura plana)
        csv_data = {
            "call_id": self.metrics["call_id"],
            "timestamp": self.metrics["timestamp"],
            "total_duration": self.metrics["duration"]["total"],
            "stt_duration": self.metrics["duration"]["stt"],
            "llm_duration": self.metrics["duration"]["llm"],
            "tts_duration": self.metrics["duration"]["tts"],
            "faiss_duration": self.metrics["duration"]["faiss"],
            "input_tokens": self.metrics["tokens"]["input"],
            "output_tokens": self.metrics["tokens"]["output"],
            "total_tokens": self.metrics["tokens"]["total"],
            "stt_cost": self.metrics["costs"]["stt"],
            "llm_cost": self.metrics["costs"]["llm"],
            "tts_cost": self.metrics["costs"]["tts"],
            "total_cost": self.metrics["costs"]["total"],
            "input_size_bytes": self.metrics["audio"]["input_size_bytes"],
            "output_size_bytes": self.metrics["audio"]["output_size_bytes"],
            "input_duration_seconds": self.metrics["audio"]["input_duration_seconds"],
            "output_duration_seconds": self.metrics["audio"]["output_duration_seconds"],
            "stt_model": self.metrics["models"]["stt"],
            "llm_model": self.metrics["models"]["llm"],
            "tts_model": self.metrics["models"]["tts"],
            "stt_success": self.metrics["status"]["stt_success"],
            "llm_success": self.metrics["status"]["llm_success"],
            "tts_success": self.metrics["status"]["tts_success"],
            "overall_success": self.metrics["status"]["overall_success"],
            "faiss_used": self.metrics["faiss"]["used"],
            "faiss_found_answer": self.metrics["faiss"]["found_answer"],
        }
        
        # Escribir al CSV
        with open(csv_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=csv_data.keys())
            
            # Escribir encabezados si es un archivo nuevo
            if not file_exists:
                writer.writeheader()
                
            writer.writerow(csv_data)
            
        logger.info(f"Métricas añadidas al CSV en {csv_file}")


# Utilidades para estimar duración de audio
def estimate_audio_duration(file_path):
    """
    Estima la duración de un archivo de audio basado en su tamaño y formato
    
    Args:
        file_path (str): Ruta al archivo de audio
        
    Returns:
        float: Duración estimada en segundos
    """
    try:
        import wave
        
        # Si es un archivo WAV, podemos obtener la duración exacta
        if file_path.lower().endswith('.wav'):
            with wave.open(file_path, 'rb') as wav_file:
                # Duración = frames / framerate
                return wav_file.getnframes() / wav_file.getframerate()
                
        # Para otros formatos, hacemos una estimación aproximada
        # MP3 típico: ~128 kbps = 16 KB/s
        else:
            file_size = os.path.getsize(file_path)
            # Estimación muy aproximada
            bitrate = 128 * 1024 / 8  # 16 KB/s para MP3 estándar
            return file_size / bitrate
            
    except Exception as e:
        logger.warning(f"No se pudo estimar la duración del audio {file_path}: {e}")
        return 0