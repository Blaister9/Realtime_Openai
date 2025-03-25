#!/usr/bin/env python3
import sys
import os
import logging
import traceback

# Importar módulos refactorizados
import config
from knowledge_base import initialize_faiss, get_faq_answer
from audio_processor import validate_audio_file, read_audio_file, transcribe_audio, text_to_speech
from openai_client import (
    create_openai_headers, 
    create_llm_payload, 
    create_second_llm_payload, 
    send_openai_request, 
    process_llm_response, 
    extract_function_args
)
from file_utils import create_required_directories, save_audio_response, create_exit_flag
from metrics_tracker import CallMetrics, estimate_audio_duration

# Configurar logger
logger = logging.getLogger(__name__)

def main():
    """Función principal del asistente virtual - Implementa arquitectura encadenada (STT → LLM → TTS)"""
    logger.info("==== INICIO DEL SCRIPT asistente_virtual.py (Arquitectura Encadenada) ====")
    logger.info("Entrando a función main()")
    
    # Verificar argumentos
    if len(sys.argv) < 2:
        logger.error("Uso: asistente_virtual.py <ruta_wav>")
        sys.exit(1)
    
    # Obtener ruta del archivo de audio
    user_input_wav = sys.argv[1]
    logger.info(f"Archivo de entrada: {user_input_wav}")
    
    # Validar archivo de audio
    if not validate_audio_file(user_input_wav):
        sys.exit(1)
    
    # Verificar clave API de OpenAI
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        logger.error("La clave API de OpenAI no está configurada en las variables de entorno.")
        sys.exit(1)
    else:
        logger.info("API key de OpenAI configurada correctamente")
    
    # Inicializar FAISS
    faiss_initialized = initialize_faiss()
    logger.info(f"Estado de inicialización FAISS: {'Disponible' if faiss_initialized else 'No disponible'}")
    
    # Inicializar tracker de métricas
    metrics = CallMetrics(config.BASE_DIR)
    
    # Registrar modelos utilizados
    metrics.set_models(
        stt_model=config.OPENAI_STT_MODEL,
        llm_model=config.OPENAI_LLM_MODEL,
        tts_model=config.OPENAI_TTS_MODEL
    )
    
    # Registrar métricas de audio de entrada
    input_size = os.path.getsize(user_input_wav)
    input_duration = estimate_audio_duration(user_input_wav)
    metrics.set_audio_metrics(input_size=input_size, input_duration=input_duration)
    
    try:
        # PASO 1: Transcribir audio a texto (STT)
        # ------------------------------------------------------------
        logger.info("PASO 1: Transcribiendo audio a texto (STT)")
        metrics.start_step("stt")
        transcript = transcribe_audio(user_input_wav, OPENAI_API_KEY)
        metrics.end_step("stt")
        
        if not transcript:
            logger.error("No se pudo transcribir el audio")
            metrics.set_status(stt_success=False)
            metrics.finalize()
            sys.exit(1)
        
        # Registrar transcripción y estado de éxito
        metrics.set_transcript(user_input=transcript)
        metrics.set_status(stt_success=True)
        logger.info(f"Transcripción: {transcript}")
        
        # PASO 2: Procesar texto con el LLM
        # ------------------------------------------------------------
        logger.info("PASO 2: Procesando texto con el LLM")
        metrics.start_step("llm")
        
        # Crear cabeceras y payload para la API
        headers = create_openai_headers(OPENAI_API_KEY)
        llm_payload = create_llm_payload(transcript)
        
        # Enviar solicitud al LLM
        llm_response = send_openai_request(headers, llm_payload)
        if not llm_response:
            logger.error("Falló la llamada al LLM")
            metrics.set_status(stt_success=True, llm_success=False)
            metrics.finalize()
            sys.exit(1)
        
        # Procesar respuesta del LLM
        tool_calls, assistant_response, should_exit = process_llm_response(llm_response)
        
        # Registrar uso de tokens si está disponible
        if "usage" in llm_response:
            usage = llm_response["usage"]
            metrics.set_token_usage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0)
            )
        
        # Si hay llamadas a funciones, procesar y hacer segunda llamada
        if tool_calls:
            for tool_call in tool_calls:
                if tool_call["function"]["name"] == "get_faq_answer":
                    # Registrar uso de FAISS
                    metrics.set_faiss_metrics(used=True)
                    metrics.start_step("faiss")
                    
                    # Extraer pregunta y buscar en FAISS
                    question = extract_function_args(tool_call)
                    if question:
                        # Buscar en la base de conocimiento
                        faiss_response = get_faq_answer(question)
                        faiss_found = faiss_response is not None
                        logger.info(f"Respuesta FAISS obtenida: {faiss_found}")
                        
                        # Actualizar métricas de FAISS
                        metrics.set_faiss_metrics(used=True, found_answer=faiss_found)
                        metrics.end_step("faiss")
                        
                        if faiss_response:
                            metrics.set_transcript(faiss_response=faiss_response)
                        
                        # Segunda llamada al LLM con el resultado de FAISS
                        second_payload = create_second_llm_payload(transcript, tool_calls, faiss_response)
                        
                        # Enviar segunda solicitud
                        logger.info("Enviando segunda solicitud al LLM con resultado de FAISS...")
                        second_llm_response = send_openai_request(headers, second_payload)
                        
                        if second_llm_response:
                            logger.info("Segunda solicitud exitosa, usando esta respuesta")
                            # Actualizar con nueva información procesada
                            _, assistant_response, should_exit = process_llm_response(second_llm_response)
                            
                            # Actualizar métricas de tokens para incluir la segunda llamada
                            if "usage" in second_llm_response:
                                usage = second_llm_response["usage"]
                                current_input = metrics.metrics["tokens"]["input"]
                                current_output = metrics.metrics["tokens"]["output"]
                                metrics.set_token_usage(
                                    input_tokens=current_input + usage.get("prompt_tokens", 0),
                                    output_tokens=current_output + usage.get("completion_tokens", 0)
                                )
        
        # Finalizar métricas del paso LLM
        metrics.end_step("llm")
        
        # Registrar respuesta del asistente y estado
        metrics.set_transcript(assistant_response=assistant_response)
        metrics.set_status(stt_success=True, llm_success=True)
        
        # PASO 3: Convertir respuesta a voz (TTS)
        # ------------------------------------------------------------
        if assistant_response:
            logger.info("PASO 3: Convirtiendo respuesta a voz (TTS)")
            metrics.start_step("tts")
            
            logger.info(f"Texto a convertir: {assistant_response}")
            
            # Convertir texto a voz
            speech_instructions = "Hablar en un tono natural y profesional para un sistema IVR."
            audio_response = text_to_speech(assistant_response, OPENAI_API_KEY, instructions=speech_instructions)
            
            if not audio_response:
                logger.error("No se pudo convertir el texto a voz")
                metrics.set_status(stt_success=True, llm_success=True, tts_success=False)
                metrics.finalize()
                sys.exit(1)
            
            # Actualizar métricas de TTS
            metrics.end_step("tts")
            metrics.set_status(stt_success=True, llm_success=True, tts_success=True)
            
            # Actualizar métricas de audio de salida
            output_size = len(audio_response)
            # Estimación aproximada de duración del audio generado (TTS)
            output_duration = len(assistant_response) * 0.07  # Aproximadamente 70ms por carácter
            metrics.set_audio_metrics(
                input_size=input_size,
                output_size=output_size,
                input_duration=input_duration,
                output_duration=output_duration
            )
                
            # Guardar respuesta de audio
            if save_audio_response(audio_response, config.RESPONSE_PATH):
                logger.info(f"Respuesta de audio guardada exitosamente")
            else:
                logger.error("Error guardando respuesta de audio")
                sys.exit(1)
        else:
            logger.error("No se obtuvo respuesta del LLM")
            metrics.set_status(stt_success=True, llm_success=False, tts_success=False)
            metrics.finalize()
            sys.exit(1)
        
        # Si el usuario pidió salir, crear bandera
        if should_exit:
            logger.info("Creando bandera de salida por solicitud del usuario")
            create_exit_flag()
        
        # Finalizar y guardar todas las métricas
        final_metrics = metrics.finalize()
        logger.info(f"Métricas finales: Duración total={final_metrics['duration']['total']}s, Costo total=${final_metrics['costs']['total']}")
        
    except Exception as e:
        logger.critical(f"Error en la ejecución: {e}")
        logger.critical(traceback.format_exc())
        
        # Intentar finalizar métricas incluso en caso de error
        try:
            if 'metrics' in locals():
                metrics.finalize()
        except:
            pass
            
        sys.exit(1)
        
    logger.info("==== FIN DEL SCRIPT asistente_virtual.py ====")

if __name__ == "__main__":
    try:
        # Inicializar entorno y configuración
        create_required_directories(config.BASE_DIR)
        
        # Crear directorios adicionales para métricas
        os.makedirs(os.path.join(config.BASE_DIR, "metrics"), exist_ok=True)
        os.makedirs(os.path.join(config.BASE_DIR, "transcripts"), exist_ok=True)
        
        config.setup_environment()
        
        # Ejecutar función principal
        main()
    except Exception as e:
        logger.critical(f"Excepción no controlada: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)