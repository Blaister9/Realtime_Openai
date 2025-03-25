#!/usr/bin/env python3
import logging
import time
import traceback
import sys

logger = logging.getLogger(__name__)

# Variable global para indicar disponibilidad de FAISS
FAISS_AVAILABLE = False

def initialize_faiss():
    """Intenta inicializar el módulo FAISS"""
    global FAISS_AVAILABLE
    
    try:
        logger.info("Intentando importar numpy")
        import numpy as np
        logger.info("NumPy importado correctamente")
        
        logger.info("Intentando importar faiss_search desde embeddings.buscar_pregunta")
        from embeddings.buscar_pregunta import faiss_search
        logger.info("Módulo FAISS importado correctamente")
        
        FAISS_AVAILABLE = True
        return True
        
    except ImportError as e:
        logger.error(f"Error importando módulos para FAISS: {e}")
        logger.error(traceback.format_exc())
        FAISS_AVAILABLE = False
        return False

def get_faq_answer(question):
    """
    Busca respuestas en la base de conocimiento usando FAISS
    
    Args:
        question (str): La pregunta o consulta del usuario
        
    Returns:
        str or None: Respuesta encontrada o None si no hay coincidencias
    """
    logger.debug(f"Llamada a get_faq_answer con pregunta: {question[:100]}...")

    if not FAISS_AVAILABLE:
        logger.warning("FAISS no está disponible, omitiendo búsqueda de conocimiento")
        return None
    
    try:
        # Importamos aquí nuevamente para asegurar que esté disponible
        from embeddings.buscar_pregunta import faiss_search
        
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

def diagnostic_faiss_search(transcript):
    """
    Realiza una búsqueda de diagnóstico en FAISS para verificar su funcionamiento
    
    Args:
        transcript (str): Texto de transcripción para buscar
        
    Returns:
        bool: True si FAISS encontró una respuesta, False en caso contrario
    """
    if not FAISS_AVAILABLE:
        logger.warning("FAISS no disponible para diagnóstico")
        return False
        
    try:
        diag_faiss = get_faq_answer(transcript)
        if diag_faiss:
            logger.info("FAISS encontró una respuesta en la transcripción diagnóstica")
            return True
        else:
            logger.info("FAISS no encontró respuestas en la transcripción diagnóstica")
            return False
    except Exception as e:
        logger.error(f"Error en diagnóstico FAISS: {e}")
        return False