#!/usr/bin/env python3
import os
import logging
import traceback
from config import EXIT_FLAG_PATH

logger = logging.getLogger(__name__)

def create_required_directories(base_dir):
    """
    Crea los directorios necesarios si no existen
    
    Args:
        base_dir (str): Directorio base
        
    Returns:
        bool: True si los directorios fueron creados o ya existían
    """
    try:
        os.makedirs(os.path.join(base_dir, "logs"), exist_ok=True)
        os.makedirs(os.path.join(base_dir, "tmp"), exist_ok=True)
        logger.info(f"Directorios requeridos verificados en {base_dir}")
        return True
    except Exception as e:
        logger.error(f"Error creando directorios: {e}")
        logger.error(traceback.format_exc())
        return False

def save_audio_response(audio_data, output_path):
    """
    Guarda los datos de audio en un archivo y establece permisos
    
    Args:
        audio_data (bytes): Datos de audio
        output_path (str): Ruta donde guardar el archivo
        
    Returns:
        bool: True si se guardó correctamente, False en caso contrario
    """
    try:
        logger.debug(f"Guardando audio en {output_path}")
        with open(output_path, "wb") as f:
            f.write(audio_data)
        
        # Verificar el archivo guardado
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"Respuesta generada y guardada en {output_path} (tamaño: {file_size} bytes)")
            
            # Establecer permisos adecuados
            try:
                os.chmod(output_path, 0o644)  # rw-r--r--
                logger.info(f"Permisos establecidos en el archivo de audio")
            except Exception as e:
                logger.warning(f"No se pudieron establecer permisos: {e}")
            
            return True
        else:
            logger.error(f"El archivo no existe después de guardar")
            return False
            
    except Exception as e:
        logger.error(f"No se pudo guardar el archivo de audio de respuesta: {e}")
        logger.error(traceback.format_exc())
        return False

def create_exit_flag():
    """
    Crea un archivo de bandera para indicar que se debe finalizar la conversación
    
    Returns:
        bool: True si se creó correctamente, False en caso contrario
    """
    try:
        with open(EXIT_FLAG_PATH, "w") as f:
            f.write("1")
        logger.info(f"Bandera de salida creada en {EXIT_FLAG_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error creando bandera de salida: {e}")
        logger.error(traceback.format_exc())
        return False