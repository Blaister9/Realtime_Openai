import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import io
import os
import base64
import xlsxwriter

# Configuración inicial de la página
st.set_page_config(
    page_title="Sistema de Gestión de Recursos Humanos",
    page_icon="👥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplicar algunos estilos CSS personalizados
st.markdown("""
<style>
    .main-header {
        font-size: 30px;
        font-weight: bold;
        color: #2c3e50;
        margin-bottom: 20px;
    }
    .section-header {
        font-size: 24px;
        font-weight: bold;
        color: #3498db;
        margin-top: 30px;
        margin-bottom: 10px;
    }
    .subsection-header {
        font-size: 18px;
        font-weight: bold;
        margin-top: 15px;
        margin-bottom: 10px;
    }
    .success-message {
        color: #27ae60;
        font-weight: bold;
    }
    .error-message {
        color: #e74c3c;
        font-weight: bold;
    }
    .help-text {
        color: #7f8c8d;
        font-style: italic;
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Inicialización de la base de datos
def init_db():
    conn = sqlite3.connect('rrhh.db')
    c = conn.cursor()
    
    # Tabla de cargos
    c.execute('''
    CREATE TABLE IF NOT EXISTS cargos (
        id INTEGER PRIMARY KEY,
        nombre_cargo TEXT NOT NULL,
        nomenclatura TEXT NOT NULL,
        nivel TEXT NOT NULL,
        naturaleza TEXT NOT NULL,
        asignacion_basica REAL NOT NULL,
        decreto_creacion TEXT,
        estado TEXT DEFAULT 'Activo',
        fecha_creacion TEXT NOT NULL,
        fecha_modificacion TEXT,
        ubicacion TEXT,
        dependencia TEXT,
        jefe INTEGER,
        prima_tecnica REAL DEFAULT 0,
        observaciones TEXT
    )
    ''')
    
    # Tabla de servidores públicos
    c.execute('''
    CREATE TABLE IF NOT EXISTS servidores (
        id INTEGER PRIMARY KEY,
        documento_identidad TEXT UNIQUE NOT NULL,
        tipo_documento TEXT NOT NULL,
        nombres TEXT NOT NULL,
        apellidos TEXT NOT NULL,
        email TEXT UNIQUE,
        telefono TEXT,
        direccion TEXT,
        fecha_nacimiento TEXT,
        genero TEXT,
        estado TEXT DEFAULT 'Activo',
        fecha_creacion TEXT NOT NULL,
        fecha_modificacion TEXT
    )
    ''')
    
    # Tabla de vinculaciones (histórico)
    c.execute('''
    CREATE TABLE IF NOT EXISTS vinculaciones (
        id INTEGER PRIMARY KEY,
        servidor_id INTEGER NOT NULL,
        cargo_id INTEGER NOT NULL,
        fecha_inicio TEXT NOT NULL,
        fecha_fin TEXT,
        tipo_vinculacion TEXT NOT NULL,
        resolucion_vinculacion TEXT,
        acta_posesion TEXT,
        observaciones TEXT,
        FOREIGN KEY (servidor_id) REFERENCES servidores (id),
        FOREIGN KEY (cargo_id) REFERENCES cargos (id)
    )
    ''')
    
    # Tabla de traslados
    c.execute('''
    CREATE TABLE IF NOT EXISTS traslados (
        id INTEGER PRIMARY KEY,
        vinculacion_id INTEGER NOT NULL,
        cargo_origen_id INTEGER NOT NULL,
        cargo_destino_id INTEGER NOT NULL,
        fecha_traslado TEXT NOT NULL,
        resolucion_traslado TEXT,
        motivo_traslado TEXT,
        observaciones TEXT,
        FOREIGN KEY (vinculacion_id) REFERENCES vinculaciones (id),
        FOREIGN KEY (cargo_origen_id) REFERENCES cargos (id),
        FOREIGN KEY (cargo_destino_id) REFERENCES cargos (id)
    )
    ''')
    
    # Tabla de dependencias
    c.execute('''
    CREATE TABLE IF NOT EXISTS dependencias (
        id INTEGER PRIMARY KEY,
        nombre TEXT UNIQUE NOT NULL,
        codigo TEXT UNIQUE,
        descripcion TEXT,
        fecha_creacion TEXT NOT NULL
    )
    ''')
    
    # Tabla de usuarios del sistema
    c.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        nombre_completo TEXT NOT NULL,
        rol TEXT NOT NULL,
        estado TEXT DEFAULT 'Activo',
        ultimo_acceso TEXT
    )
    ''')
    
    # Insertar datos iniciales si no existen
    
    # Insertar dependencias iniciales
    c.execute("SELECT COUNT(*) FROM dependencias")
    if c.fetchone()[0] == 0:
        dependencias = [
            ('Dirección General', 'DG', 'Dirección General de la Agencia', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            ('Subdirección Administrativa', 'SA', 'Subdirección Administrativa', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            ('Subdirección Técnica', 'ST', 'Subdirección Técnica', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            ('Oficina de Planeación', 'OP', 'Oficina de Planeación', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            ('Oficina Jurídica', 'OJ', 'Oficina Jurídica', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            ('Recursos Humanos', 'RH', 'Gestión de Recursos Humanos', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        ]
        c.executemany("INSERT INTO dependencias (nombre, codigo, descripcion, fecha_creacion) VALUES (?, ?, ?, ?)", dependencias)
    
    # Insertar cargos iniciales
    c.execute("SELECT COUNT(*) FROM cargos")
    if c.fetchone()[0] == 0:
        cargos = [
            (1, 'Director General', 'DG', 'Directivo', 'Libre Nombramiento', 12500000, 'Decreto 123 de 2020', 'Activo', 
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), None, 'Sede Principal', 'Dirección General', None, 50, None),
            (2, 'Subdirector Administrativo', 'SA', 'Directivo', 'Libre Nombramiento', 10000000, 'Decreto 123 de 2020', 'Activo', 
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), None, 'Sede Principal', 'Subdirección Administrativa', 1, 40, None),
            (3, 'Subdirector Técnico', 'ST', 'Directivo', 'Libre Nombramiento', 10000000, 'Decreto 123 de 2020', 'Activo', 
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), None, 'Sede Principal', 'Subdirección Técnica', 1, 40, None),
            (4, 'Jefe de Oficina', 'JO', 'Directivo', 'Libre Nombramiento', 9000000, 'Decreto 123 de 2020', 'Activo', 
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), None, 'Sede Principal', 'Oficina de Planeación', 1, 30, None),
            (5, 'Profesional Especializado', 'PE', 'Profesional', 'Carrera', 7000000, 'Decreto 123 de 2020', 'Activo', 
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), None, 'Sede Principal', 'Recursos Humanos', 2, 20, None),
            (6, 'Profesional Universitario', 'PU', 'Profesional', 'Carrera', 5500000, 'Decreto 123 de 2020', 'Activo', 
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), None, 'Sede Principal', 'Oficina Jurídica', 4, 15, None),
            (7, 'Técnico Administrativo', 'TA', 'Técnico', 'Carrera', 3500000, 'Decreto 123 de 2020', 'Activo', 
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), None, 'Sede Principal', 'Subdirección Administrativa', 2, 0, None),
            (8, 'Auxiliar Administrativo', 'AA', 'Asistencial', 'Carrera', 2500000, 'Decreto 123 de 2020', 'Activo', 
             datetime.now().strftime('%Y-%m-%d %H:%M:%S'), None, 'Sede Principal', 'Recursos Humanos', 5, 0, None)
        ]
        c.executemany('''
            INSERT INTO cargos 
            (id, nombre_cargo, nomenclatura, nivel, naturaleza, asignacion_basica, decreto_creacion, estado, 
            fecha_creacion, fecha_modificacion, ubicacion, dependencia, jefe, prima_tecnica, observaciones) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', cargos)
    
    # Insertar usuario administrador por defecto
    c.execute("SELECT COUNT(*) FROM usuarios")
    if c.fetchone()[0] == 0:
        # Contraseña "admin123" - En producción usaríamos hash
        c.execute("INSERT INTO usuarios (username, password, nombre_completo, rol) VALUES (?, ?, ?, ?)", 
                 ('admin', 'admin123', 'Administrador del Sistema', 'admin'))
    
    conn.commit()
    conn.close()

# Función para obtener conexión a la base de datos
def get_db_connection():
    conn = sqlite3.connect('rrhh.db')
    conn.row_factory = sqlite3.Row
    return conn

# Función para autenticación
def authenticate(username, password):
    conn = get_db_connection()
    user = conn.execute(
        "SELECT * FROM usuarios WHERE username = ? AND password = ? AND estado = 'Activo'", 
        (username, password)
    ).fetchone()
    conn.close()
    
    if user:
        # Actualizar último acceso
        conn = get_db_connection()
        conn.execute(
            "UPDATE usuarios SET ultimo_acceso = ? WHERE id = ?",
            (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), user['id'])
        )
        conn.commit()
        conn.close()
        
        return dict(user)
    return None

# Función para exportar a Excel
def generate_excel(data, filename):
    df = pd.DataFrame(data)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, index=False, sheet_name='Datos')
    writer.close()
    
    b64 = base64.b64encode(output.getvalue()).decode()
    href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="{filename}.xlsx">Descargar Excel</a>'
    return href

# Funciones para gestión de cargos
def get_all_cargos():
    conn = get_db_connection()
    cargos = conn.execute("SELECT * FROM cargos ORDER BY nombre_cargo").fetchall()
    conn.close()
    return cargos

def get_cargo_by_id(cargo_id):
    conn = get_db_connection()
    cargo = conn.execute("SELECT * FROM cargos WHERE id = ?", (cargo_id,)).fetchone()
    conn.close()
    return cargo

def add_cargo(cargo_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verificar si se especificó un ID personalizado y si está disponible
    if cargo_data.get('id_personalizado') and cargo_data['id_personalizado'] > 0:
        # Verificar si el ID ya existe
        existing = cursor.execute("SELECT COUNT(*) FROM cargos WHERE id = ?", 
                                 (cargo_data['id_personalizado'],)).fetchone()[0]
        if existing > 0:
            conn.close()
            return False, "El ID especificado ya está en uso."
        
        cargo_id = cargo_data['id_personalizado']
    else:
        # Obtener el próximo ID disponible
        max_id = cursor.execute("SELECT MAX(id) FROM cargos").fetchone()[0] or 0
        cargo_id = max_id + 1
    
    cursor.execute('''
        INSERT INTO cargos 
        (id, nombre_cargo, nomenclatura, nivel, naturaleza, asignacion_basica, decreto_creacion, estado, 
        fecha_creacion, ubicacion, dependencia, jefe, prima_tecnica, observaciones) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        cargo_id,
        cargo_data['nombre_cargo'],
        cargo_data['nomenclatura'],
        cargo_data['nivel'],
        cargo_data['naturaleza'],
        cargo_data['asignacion_basica'],
        cargo_data['decreto_creacion'],
        cargo_data['estado'],
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        cargo_data['ubicacion'],
        cargo_data['dependencia'],
        cargo_data['jefe'] if cargo_data['jefe'] else None,
        cargo_data['prima_tecnica'],
        cargo_data['observaciones']
    ))
    
    conn.commit()
    conn.close()
    return True, cargo_id

def update_cargo(cargo_id, cargo_data):
    conn = get_db_connection()
    
    conn.execute('''
        UPDATE cargos SET 
        nombre_cargo = ?, 
        nomenclatura = ?, 
        nivel = ?, 
        naturaleza = ?, 
        asignacion_basica = ?, 
        decreto_creacion = ?, 
        estado = ?, 
        fecha_modificacion = ?,
        ubicacion = ?,
        dependencia = ?, 
        jefe = ?, 
        prima_tecnica = ?, 
        observaciones = ? 
        WHERE id = ?
    ''', (
        cargo_data['nombre_cargo'],
        cargo_data['nomenclatura'],
        cargo_data['nivel'],
        cargo_data['naturaleza'],
        cargo_data['asignacion_basica'],
        cargo_data['decreto_creacion'],
        cargo_data['estado'],
        datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        cargo_data['ubicacion'],
        cargo_data['dependencia'],
        cargo_data['jefe'] if cargo_data['jefe'] else None,
        cargo_data['prima_tecnica'],
        cargo_data['observaciones'],
        cargo_id
    ))
    
    conn.commit()
    conn.close()
    return True

def delete_cargo(cargo_id):
    conn = get_db_connection()
    
    # Verificar si el cargo está siendo utilizado en vinculaciones
    vinculaciones = conn.execute("SELECT COUNT(*) FROM vinculaciones WHERE cargo_id = ?", (cargo_id,)).fetchone()[0]
    
    if vinculaciones > 0:
        conn.close()
        return False, "No se puede eliminar el cargo porque tiene vinculaciones asociadas."
    
    conn.execute("DELETE FROM cargos WHERE id = ?", (cargo_id,))
    conn.commit()
    conn.close()
    return True, "Cargo eliminado correctamente."

# Funciones para gestión de servidores
def get_all_servidores():
    conn = get_db_connection()
    servidores = conn.execute("SELECT * FROM servidores ORDER BY apellidos, nombres").fetchall()
    conn.close()
    return servidores

def get_servidor_by_id(servidor_id):
    conn = get_db_connection()
    servidor = conn.execute("SELECT * FROM servidores WHERE id = ?", (servidor_id,)).fetchone()
    conn.close()
    return servidor

def add_servidor(servidor_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO servidores 
            (documento_identidad, tipo_documento, nombres, apellidos, email, telefono, direccion, 
            fecha_nacimiento, genero, estado, fecha_creacion) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            servidor_data['documento_identidad'],
            servidor_data['tipo_documento'],
            servidor_data['nombres'],
            servidor_data['apellidos'],
            servidor_data['email'],
            servidor_data['telefono'],
            servidor_data['direccion'],
            servidor_data['fecha_nacimiento'],
            servidor_data['genero'],
            'Activo',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))
        
        servidor_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return True, servidor_id
    except sqlite3.IntegrityError as e:
        conn.close()
        if "UNIQUE constraint failed: servidores.documento_identidad" in str(e):
            return False, "Ya existe un servidor con ese documento de identidad."
        elif "UNIQUE constraint failed: servidores.email" in str(e):
            return False, "Ya existe un servidor con ese correo electrónico."
        else:
            return False, str(e)

def update_servidor(servidor_id, servidor_data):
    conn = get_db_connection()
    
    try:
        conn.execute('''
            UPDATE servidores SET 
            documento_identidad = ?, 
            tipo_documento = ?, 
            nombres = ?, 
            apellidos = ?, 
            email = ?, 
            telefono = ?, 
            direccion = ?, 
            fecha_nacimiento = ?, 
            genero = ?, 
            estado = ?, 
            fecha_modificacion = ? 
            WHERE id = ?
        ''', (
            servidor_data['documento_identidad'],
            servidor_data['tipo_documento'],
            servidor_data['nombres'],
            servidor_data['apellidos'],
            servidor_data['email'],
            servidor_data['telefono'],
            servidor_data['direccion'],
            servidor_data['fecha_nacimiento'],
            servidor_data['genero'],
            servidor_data['estado'],
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            servidor_id
        ))
        
        conn.commit()
        conn.close()
        return True, "Servidor actualizado correctamente."
    except sqlite3.IntegrityError as e:
        conn.close()
        if "UNIQUE constraint failed: servidores.documento_identidad" in str(e):
            return False, "Ya existe otro servidor con ese documento de identidad."
        elif "UNIQUE constraint failed: servidores.email" in str(e):
            return False, "Ya existe otro servidor con ese correo electrónico."
        else:
            return False, str(e)

# Funciones para gestión de vinculaciones
def get_vinculaciones_by_servidor(servidor_id):
    conn = get_db_connection()
    vinculaciones = conn.execute('''
        SELECT v.*, c.nombre_cargo, c.nomenclatura, c.asignacion_basica, c.dependencia
        FROM vinculaciones v
        JOIN cargos c ON v.cargo_id = c.id
        WHERE v.servidor_id = ?
        ORDER BY v.fecha_inicio DESC
    ''', (servidor_id,)).fetchall()
    conn.close()
    return vinculaciones

def add_vinculacion(vinculacion_data):
    conn = get_db_connection()
    
    # Verificar si hay una vinculación activa para el servidor
    if vinculacion_data['fecha_fin'] is None or vinculacion_data['fecha_fin'] == '':
        active_vinculacion = conn.execute('''
            SELECT COUNT(*) FROM vinculaciones 
            WHERE servidor_id = ? AND fecha_fin IS NULL
        ''', (vinculacion_data['servidor_id'],)).fetchone()[0]
        
        if active_vinculacion > 0:
            conn.close()
            return False, "El servidor ya tiene una vinculación activa. Finalice la vinculación actual antes de crear una nueva."
    
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO vinculaciones 
        (servidor_id, cargo_id, fecha_inicio, fecha_fin, tipo_vinculacion, 
        resolucion_vinculacion, acta_posesion, observaciones) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        vinculacion_data['servidor_id'],
        vinculacion_data['cargo_id'],
        vinculacion_data['fecha_inicio'],
        vinculacion_data['fecha_fin'] if vinculacion_data['fecha_fin'] else None,
        vinculacion_data['tipo_vinculacion'],
        vinculacion_data['resolucion_vinculacion'],
        vinculacion_data['acta_posesion'],
        vinculacion_data['observaciones']
    ))
    
    vinculacion_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return True, vinculacion_id

def update_vinculacion(vinculacion_id, vinculacion_data):
    conn = get_db_connection()
    
    conn.execute('''
        UPDATE vinculaciones SET 
        cargo_id = ?, 
        fecha_inicio = ?, 
        fecha_fin = ?, 
        tipo_vinculacion = ?, 
        resolucion_vinculacion = ?, 
        acta_posesion = ?, 
        observaciones = ? 
        WHERE id = ?
    ''', (
        vinculacion_data['cargo_id'],
        vinculacion_data['fecha_inicio'],
        vinculacion_data['fecha_fin'] if vinculacion_data['fecha_fin'] else None,
        vinculacion_data['tipo_vinculacion'],
        vinculacion_data['resolucion_vinculacion'],
        vinculacion_data['acta_posesion'],
        vinculacion_data['observaciones'],
        vinculacion_id
    ))
    
    conn.commit()
    conn.close()
    return True

def get_traslados_by_vinculacion(vinculacion_id):
    conn = get_db_connection()
    traslados = conn.execute('''
        SELECT t.*, 
               c1.nombre_cargo as cargo_origen_nombre,
               c2.nombre_cargo as cargo_destino_nombre
        FROM traslados t
        JOIN cargos c1 ON t.cargo_origen_id = c1.id
        JOIN cargos c2 ON t.cargo_destino_id = c2.id
        WHERE t.vinculacion_id = ?
        ORDER BY t.fecha_traslado DESC
    ''', (vinculacion_id,)).fetchall()
    conn.close()
    return traslados

def add_traslado(traslado_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO traslados 
        (vinculacion_id, cargo_origen_id, cargo_destino_id, fecha_traslado, 
        resolucion_traslado, motivo_traslado, observaciones) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        traslado_data['vinculacion_id'],
        traslado_data['cargo_origen_id'],
        traslado_data['cargo_destino_id'],
        traslado_data['fecha_traslado'],
        traslado_data['resolucion_traslado'],
        traslado_data['motivo_traslado'],
        traslado_data['observaciones']
    ))
    
    # Actualizar el cargo en la vinculación
    conn.execute('''
        UPDATE vinculaciones SET cargo_id = ? WHERE id = ?
    ''', (traslado_data['cargo_destino_id'], traslado_data['vinculacion_id']))
    
    conn.commit()
    conn.close()
    return True

# Funciones para gestión de dependencias
def get_all_dependencias():
    conn = get_db_connection()
    dependencias = conn.execute("SELECT * FROM dependencias ORDER BY nombre").fetchall()
    conn.close()
    return dependencias

# Función para obtener los cargos disponibles para un jefe
def get_cargos_for_jefe():
    conn = get_db_connection()
    cargos = conn.execute('''
        SELECT id, nombre_cargo, nomenclatura 
        FROM cargos 
        WHERE nivel = 'Directivo' OR nivel = 'Asesor'
        ORDER BY nivel, nombre_cargo
    ''').fetchall()
    conn.close()
    return cargos

# Función para generar certificación laboral
def generar_certificacion_laboral(servidor_id, fecha_inicio, fecha_fin):
    conn = get_db_connection()
    
    # Obtener datos del servidor
    servidor = conn.execute("SELECT * FROM servidores WHERE id = ?", (servidor_id,)).fetchone()
    
    if not servidor:
        conn.close()
        return None, "No se encontró el servidor especificado."
    
    # Obtener vinculaciones en el periodo solicitado
    vinculaciones = conn.execute('''
        SELECT v.*, c.nombre_cargo, c.nomenclatura, c.nivel, c.asignacion_basica, c.dependencia
        FROM vinculaciones v
        JOIN cargos c ON v.cargo_id = c.id
        WHERE v.servidor_id = ? AND 
              ((v.fecha_inicio <= ? AND (v.fecha_fin >= ? OR v.fecha_fin IS NULL)) OR
               (v.fecha_inicio >= ? AND v.fecha_inicio <= ?))
        ORDER BY v.fecha_inicio
    ''', (servidor_id, fecha_fin, fecha_inicio, fecha_inicio, fecha_fin)).fetchall()
    
    if not vinculaciones:
        conn.close()
        return None, "No se encontraron vinculaciones en el periodo especificado."
    
    conn.close()
    
    # Generar texto de la certificación
    certificacion = {
        'servidor': dict(servidor),
        'vinculaciones': [dict(v) for v in vinculaciones],
        'fecha_generacion': datetime.now().strftime('%Y-%m-%d'),
        'periodo': f"del {fecha_inicio} al {fecha_fin}"
    }
    
    return certificacion, None

# Función para buscar cargos vacantes
def buscar_cargos_vacantes():
    conn = get_db_connection()
    
    # Obtener todos los cargos activos
    cargos_activos = conn.execute('''
        SELECT id FROM cargos WHERE estado = 'Activo'
    ''').fetchall()
    
    cargos_vacantes = []
    
    # Verificar cuáles no tienen una vinculación activa
    for cargo in cargos_activos:
        cargo_id = cargo['id']
        
        # Verificar si hay alguna vinculación activa para este cargo
        vinculacion_activa = conn.execute('''
            SELECT COUNT(*) FROM vinculaciones 
            WHERE cargo_id = ? AND fecha_fin IS NULL
        ''', (cargo_id,)).fetchone()[0]
        
        if vinculacion_activa == 0:
            # No hay vinculación activa, el cargo está vacante
            cargo_info = conn.execute('''
                SELECT c.*, d.nombre as nombre_dependencia 
                FROM cargos c
                LEFT JOIN dependencias d ON c.dependencia = d.nombre
                WHERE c.id = ?
            ''', (cargo_id,)).fetchone()
            
            cargos_vacantes.append(dict(cargo_info))
    
    conn.close()
    return cargos_vacantes

# Función para obtener estadísticas
def obtener_estadisticas():
    conn = get_db_connection()
    
    # Total de cargos
    total_cargos = conn.execute("SELECT COUNT(*) FROM cargos").fetchone()[0]
    
    # Total de servidores
    total_servidores = conn.execute("SELECT COUNT(*) FROM servidores WHERE estado = 'Activo'").fetchone()[0]
    
    # Cargos vacantes
    cargos_vacantes = len(buscar_cargos_vacantes())
    
    # Distribución por nivel
    niveles = conn.execute('''
        SELECT nivel, COUNT(*) as cantidad 
        FROM cargos 
        GROUP BY nivel 
        ORDER BY COUNT(*) DESC
    ''').fetchall()
    
    # Distribución por dependencia
    dependencias = conn.execute('''
        SELECT dependencia, COUNT(*) as cantidad 
        FROM cargos 
        GROUP BY dependencia 
        ORDER BY COUNT(*) DESC
    ''').fetchall()
    
    # Distribución por naturaleza
    naturaleza = conn.execute('''
        SELECT naturaleza, COUNT(*) as cantidad 
        FROM cargos 
        GROUP BY naturaleza 
        ORDER BY COUNT(*) DESC
    ''').fetchall()
    
    conn.close()
    
    return {
        'total_cargos': total_cargos,
        'total_servidores': total_servidores,
        'cargos_vacantes': cargos_vacantes,
        'niveles': [dict(n) for n in niveles],
        'dependencias': [dict(d) for d in dependencias],
        'naturaleza': [dict(n) for n in naturaleza]
    }

# Función para importar datos desde Excel
def importar_excel(file, tipo):
    try:
        df = pd.read_excel(file)
        
        if tipo == 'cargos':
            # Validar columnas requeridas
            required_columns = ['nombre_cargo', 'nomenclatura', 'nivel', 'naturaleza', 'asignacion_basica']
            
            for col in required_columns:
                if col not in df.columns:
                    return False, f"El archivo no contiene la columna requerida: {col}"
            
            # Preparar los datos para inserción
            cargos_data = []
            for _, row in df.iterrows():
                cargo = {
                    'nombre_cargo': row['nombre_cargo'],
                    'nomenclatura': row['nomenclatura'],
                    'nivel': row['nivel'],
                    'naturaleza': row['naturaleza'],
                    'asignacion_basica': row['asignacion_basica'],
                    'decreto_creacion': row.get('decreto_creacion', ''),
                    'estado': 'Activo',
                    'ubicacion': row.get('ubicacion', ''),
                    'dependencia': row.get('dependencia', ''),
                    'jefe': None,
                    'prima_tecnica': row.get('prima_tecnica', 0),
                    'observaciones': row.get('observaciones', ''),
                    'id_personalizado': row.get('id', None)
                }
                
                success, _ = add_cargo(cargo)
                if not success:
                    continue
            
            return True, "Importación completada. Se han importado los cargos correctamente."
            
        elif tipo == 'servidores':
            # Validar columnas requeridas
            required_columns = ['documento_identidad', 'tipo_documento', 'nombres', 'apellidos']
            
            for col in required_columns:
                if col not in df.columns:
                    return False, f"El archivo no contiene la columna requerida: {col}"
            
            # Preparar los datos para inserción
            servidores_data = []
            for _, row in df.iterrows():
                servidor = {
                    'documento_identidad': str(row['documento_identidad']),
                    'tipo_documento': row['tipo_documento'],
                    'nombres': row['nombres'],
                    'apellidos': row['apellidos'],
                    'email': row.get('email', ''),
                    'telefono': row.get('telefono', ''),
                    'direccion': row.get('direccion', ''),
                    'fecha_nacimiento': row.get('fecha_nacimiento', ''),
                    'genero': row.get('genero', ''),
                }
                
                add_servidor(servidor)
            
            return True, "Importación completada. Se han importado los servidores correctamente."
        
        else:
            return False, "Tipo de importación no válido."
            
    except Exception as e:
        return False, f"Error al importar el archivo: {str(e)}"

# Inicializar la base de datos al inicio
init_db()

# Manejo de sesiones de usuario
if 'user' not in st.session_state:
    st.session_state.user = None

if 'page' not in st.session_state:
    st.session_state.page = 'login'

# Función para cambiar de página
def change_page(page):
    st.session_state.page = page

# Función para cerrar sesión
def logout():
    st.session_state.user = None
    change_page('login')

# Definir la barra lateral de navegación
def sidebar_menu():
    with st.sidebar:
        st.image("https://via.placeholder.com/150x150.png?text=LOGO", width=150)
        st.markdown("### Sistema de Gestión RH")
        
        st.markdown("---")
        
        if st.session_state.user:
            st.markdown(f"**Usuario:** {st.session_state.user['nombre_completo']}")
            st.markdown(f"**Rol:** {st.session_state.user['rol']}")
            st.markdown("---")
            
            st.button("📊 Dashboard", on_click=change_page, args=('dashboard',), use_container_width=True)
            st.button("👥 Gestión de Cargos", on_click=change_page, args=('cargos',), use_container_width=True)
            # Dentro de la función sidebar_menu(), cerca de donde están los otros botones
            st.button("📊 Histórico por Cargo", on_click=change_page, args=('historico_cargo',), use_container_width=True)
            st.button("👤 Gestión de Servidores", on_click=change_page, args=('servidores',), use_container_width=True)
            st.button("📑 Vinculaciones", on_click=change_page, args=('vinculaciones',), use_container_width=True)
            st.button("🔄 Traslados", on_click=change_page, args=('traslados',), use_container_width=True)
            st.button("📋 Certificaciones", on_click=change_page, args=('certificaciones',), use_container_width=True)
            st.button("📊 Reportes", on_click=change_page, args=('reportes',), use_container_width=True)
            
            if st.session_state.user['rol'] == 'admin':
                st.button("⚙️ Configuración", on_click=change_page, args=('configuracion',), use_container_width=True)
                st.button("👥 Usuarios", on_click=change_page, args=('usuarios',), use_container_width=True)
            
            st.markdown("---")
            st.button("❓ Ayuda", on_click=change_page, args=('ayuda',), use_container_width=True)
            st.button("🚪 Cerrar Sesión", on_click=logout, use_container_width=True)

# Página de login
def login_page():
    st.markdown('<h1 class="main-header">Sistema de Gestión de Recursos Humanos</h1>', unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submit = st.form_submit_button("Iniciar Sesión", use_container_width=True)
        
        if submit:
            user = authenticate(username, password)
            if user:
                st.session_state.user = user
                change_page('dashboard')
                st.experimental_rerun()
            else:
                st.error("Usuario o contraseña incorrectos")

# Página de dashboard
def dashboard_page():
    st.markdown('<h1 class="main-header">Dashboard</h1>', unsafe_allow_html=True)
    
    # Obtener estadísticas
    stats = obtener_estadisticas()
    
    # Mostrar estadísticas en tarjetas
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Total de Cargos", value=stats['total_cargos'])
    
    with col2:
        st.metric(label="Servidores Activos", value=stats['total_servidores'])
    
    with col3:
        st.metric(label="Cargos Vacantes", value=stats['cargos_vacantes'])
    
    st.markdown("---")
    
    # Gráficos
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<h3 class="section-header">Distribución por Nivel</h3>', unsafe_allow_html=True)
        
        if stats['niveles']:
            df_niveles = pd.DataFrame(stats['niveles'])
            st.bar_chart(df_niveles.set_index('nivel')['cantidad'])
        else:
            st.info("No hay datos para mostrar")
    
    with col2:
        st.markdown('<h3 class="section-header">Distribución por Naturaleza</h3>', unsafe_allow_html=True)
        
        if stats['naturaleza']:
            df_naturaleza = pd.DataFrame(stats['naturaleza'])
            st.bar_chart(df_naturaleza.set_index('naturaleza')['cantidad'])
        else:
            st.info("No hay datos para mostrar")
    
    st.markdown("---")
    
    st.markdown('<h3 class="section-header">Distribución por Dependencia</h3>', unsafe_allow_html=True)
    
    if stats['dependencias']:
        df_dependencias = pd.DataFrame(stats['dependencias'])
        st.bar_chart(df_dependencias.set_index('dependencia')['cantidad'])
    else:
        st.info("No hay datos para mostrar")
    
    st.markdown("---")
    
    # Cargos vacantes
    st.markdown('<h3 class="section-header">Cargos Vacantes</h3>', unsafe_allow_html=True)
    
    cargos_vacantes = buscar_cargos_vacantes()
    
    if cargos_vacantes:
        df_vacantes = pd.DataFrame(cargos_vacantes)
        df_vacantes = df_vacantes[['id', 'nombre_cargo', 'nomenclatura', 'nivel', 'naturaleza', 'asignacion_basica', 'dependencia']]
        st.dataframe(df_vacantes)
        
        # Opción para exportar
        if st.button("Exportar Cargos Vacantes"):
            excel_href = generate_excel(cargos_vacantes, "cargos_vacantes")
            st.markdown(excel_href, unsafe_allow_html=True)
    else:
        st.info("No hay cargos vacantes actualmente")

# Página de gestión de cargos
def cargos_page():
    st.markdown('<h1 class="main-header">Gestión de Cargos</h1>', unsafe_allow_html=True)
    
    # Crear tabs para diferentes secciones
    tab1, tab2, tab3 = st.tabs(["Listar Cargoos", "Nuevo Cargo", "Importar/Exportar"])
    
    with tab1:
        # Búsqueda y filtros
        col1, col2, col3 = st.columns(3)
        
        with col1:
            buscar = st.text_input("Buscar por nombre o nomenclatura")
        
        with col2:
            nivel_filter = st.selectbox(
                "Filtrar por nivel",
                ["Todos", "Directivo", "Asesor", "Profesional", "Técnico", "Asistencial"]
            )
        
        with col3:
            naturaleza_filter = st.selectbox(
                "Filtrar por naturaleza",
                ["Todos", "Libre Nombramiento", "Carrera"]
            )
        
        # Obtener todos los cargos
        cargos = get_all_cargos()
        
        # Aplicar filtros
        cargos_filtrados = []
        for cargo in cargos:
            # Filtro de búsqueda
            if buscar and buscar.lower() not in cargo['nombre_cargo'].lower() and buscar.lower() not in cargo['nomenclatura'].lower():
                continue
            
            # Filtro de nivel
            if nivel_filter != "Todos" and cargo['nivel'] != nivel_filter:
                continue
            
            # Filtro de naturaleza
            if naturaleza_filter != "Todos" and cargo['naturaleza'] != naturaleza_filter:
                continue
            
            cargos_filtrados.append(cargo)
        
        # Mostrar cargos
        if cargos_filtrados:
            # Convertir a dataframe para mostrar
            df_cargos = pd.DataFrame([{
                'ID': c['id'],
                'Cargo': c['nombre_cargo'],
                'Nomenclatura': c['nomenclatura'],
                'Nivel': c['nivel'],
                'Naturaleza': c['naturaleza'],
                'Asignación Básica': f"${c['asignacion_basica']:,.0f}",
                'Dependencia': c['dependencia'],
                'Estado': c['estado']
            } for c in cargos_filtrados])
            
            st.dataframe(df_cargos, use_container_width=True)
            
            # Seleccionar cargo para ver detalles o editar
            cargo_id = st.selectbox("Seleccionar cargo para ver detalles o editar", 
                               [c['id'] for c in cargos_filtrados],
                               format_func=lambda x: next((c['nombre_cargo'] for c in cargos_filtrados if c['id'] == x), ''))
            
            if cargo_id:
                cargo_seleccionado = next((c for c in cargos_filtrados if c['id'] == cargo_id), None)
                
                if cargo_seleccionado:
                    with st.expander("Detalles del Cargo", expanded=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.text_input("Nombre del Cargo", cargo_seleccionado['nombre_cargo'], key="edit_nombre_cargo")
                            st.text_input("Nomenclatura", cargo_seleccionado['nomenclatura'], key="edit_nomenclatura")
                            st.selectbox("Nivel", 
                                       ["Directivo", "Asesor", "Profesional", "Técnico", "Asistencial"],
                                       index=["Directivo", "Asesor", "Profesional", "Técnico", "Asistencial"].index(cargo_seleccionado['nivel']),
                                       key="edit_nivel")
                            st.selectbox("Naturaleza", 
                                       ["Libre Nombramiento", "Carrera"],
                                       index=["Libre Nombramiento", "Carrera"].index(cargo_seleccionado['naturaleza']),
                                       key="edit_naturaleza")
                            st.number_input("Asignación Básica", value=float(cargo_seleccionado['asignacion_basica']), key="edit_asignacion_basica")
                            st.number_input("Prima Técnica (%)", value=float(cargo_seleccionado['prima_tecnica']) if cargo_seleccionado['prima_tecnica'] else 0, key="edit_prima_tecnica")
                        
                        with col2:
                            # Obtener dependencias
                            dependencias = get_all_dependencias()
                            dependencias_nombres = [d['nombre'] for d in dependencias]
                            
                            if cargo_seleccionado['dependencia'] in dependencias_nombres:
                                dependencia_index = dependencias_nombres.index(cargo_seleccionado['dependencia'])
                            else:
                                dependencia_index = 0
                            
                            st.selectbox("Dependencia", 
                                       dependencias_nombres,
                                       index=dependencia_index,
                                       key="edit_dependencia")
                            
                            st.text_input("Ubicación", cargo_seleccionado['ubicacion'] if cargo_seleccionado['ubicacion'] else "", key="edit_ubicacion")
                            
                            # Obtener posibles jefes
                            cargos_jefes = get_cargos_for_jefe()
                            jefes_options = [{'id': None, 'nombre': 'Sin Jefe'}] + [{'id': c['id'], 'nombre': c['nombre_cargo']} for c in cargos_jefes if c['id'] != cargo_id]
                            
                            jefe_index = 0
                            for i, j in enumerate(jefes_options):
                                if j['id'] == cargo_seleccionado['jefe']:
                                    jefe_index = i
                                    break
                            
                            st.selectbox("Jefe", 
                                       range(len(jefes_options)),
                                       format_func=lambda i: jefes_options[i]['nombre'],
                                       index=jefe_index,
                                       key="edit_jefe_index")
                            
                            st.text_input("Decreto de Creación", cargo_seleccionado['decreto_creacion'] if cargo_seleccionado['decreto_creacion'] else "", key="edit_decreto_creacion")
                            
                            st.selectbox("Estado", 
                                       ["Activo", "Inactivo", "Suprimido"],
                                       index=["Activo", "Inactivo", "Suprimido"].index(cargo_seleccionado['estado']) if cargo_seleccionado['estado'] in ["Activo", "Inactivo", "Suprimido"] else 0,
                                       key="edit_estado")
                        
                        st.text_area("Observaciones", cargo_seleccionado['observaciones'] if cargo_seleccionado['observaciones'] else "", key="edit_observaciones")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("Guardar Cambios", use_container_width=True):
                                # Preparar datos actualizados
                                cargo_actualizado = {
                                    'nombre_cargo': st.session_state.edit_nombre_cargo,
                                    'nomenclatura': st.session_state.edit_nomenclatura,
                                    'nivel': st.session_state.edit_nivel,
                                    'naturaleza': st.session_state.edit_naturaleza,
                                    'asignacion_basica': st.session_state.edit_asignacion_basica,
                                    'prima_tecnica': st.session_state.edit_prima_tecnica,
                                    'dependencia': st.session_state.edit_dependencia,
                                    'ubicacion': st.session_state.edit_ubicacion,
                                    'jefe': jefes_options[st.session_state.edit_jefe_index]['id'],
                                    'decreto_creacion': st.session_state.edit_decreto_creacion,
                                    'estado': st.session_state.edit_estado,
                                    'observaciones': st.session_state.edit_observaciones
                                }
                                
                                # Actualizar cargo
                                if update_cargo(cargo_id, cargo_actualizado):
                                    st.success("Cargo actualizado correctamente")
                                    st.experimental_rerun()
                                else:
                                    st.error("Error al actualizar el cargo")
                        
                        with col2:
                            if st.button("Eliminar Cargo", use_container_width=True):
                                success, message = delete_cargo(cargo_id)
                                if success:
                                    st.success(message)
                                    st.experimental_rerun()
                                else:
                                    st.error(message)
        else:
            st.info("No se encontraron cargos con los filtros seleccionados")
    
    with tab2:
        st.markdown('<h3 class="section-header">Crear Nuevo Cargo</h3>', unsafe_allow_html=True)
        
        with st.form("nuevo_cargo_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                nombre_cargo = st.text_input("Nombre del Cargo", key="nuevo_nombre_cargo")
                nomenclatura = st.text_input("Nomenclatura", key="nuevo_nomenclatura")
                nivel = st.selectbox("Nivel", 
                                  ["Directivo", "Asesor", "Profesional", "Técnico", "Asistencial"],
                                  key="nuevo_nivel")
                naturaleza = st.selectbox("Naturaleza", 
                                       ["Libre Nombramiento", "Carrera"],
                                       key="nuevo_naturaleza")
                asignacion_basica = st.number_input("Asignación Básica", value=0.0, key="nuevo_asignacion_basica")
                prima_tecnica = st.number_input("Prima Técnica (%)", value=0.0, key="nuevo_prima_tecnica")
            
            with col2:
                # Obtener dependencias
                dependencias = get_all_dependencias()
                dependencias_nombres = [d['nombre'] for d in dependencias]
                
                dependencia = st.selectbox("Dependencia", 
                                        dependencias_nombres,
                                        key="nuevo_dependencia")
                
                ubicacion = st.text_input("Ubicación", key="nuevo_ubicacion")
                
                # Obtener posibles jefes
                cargos_jefes = get_cargos_for_jefe()
                jefes_options = [{'id': None, 'nombre': 'Sin Jefe'}] + [{'id': c['id'], 'nombre': c['nombre_cargo']} for c in cargos_jefes]
                
                jefe_index = st.selectbox("Jefe", 
                                       range(len(jefes_options)),
                                       format_func=lambda i: jefes_options[i]['nombre'],
                                       key="nuevo_jefe_index")
                
                decreto_creacion = st.text_input("Decreto de Creación", key="nuevo_decreto_creacion")
                id_personalizado = st.number_input("ID Personalizado (dejar en 0 para automático)", value=0, min_value=0, key="nuevo_id_personalizado")
            
            observaciones = st.text_area("Observaciones", key="nuevo_observaciones")
            
            submit = st.form_submit_button("Crear Cargo", use_container_width=True)
            
            if submit:
                # Validar campos requeridos
                if not nombre_cargo or not nomenclatura or not nivel or not naturaleza or asignacion_basica <= 0:
                    st.error("Por favor, complete todos los campos requeridos")
                else:
                    # Preparar datos del nuevo cargo
                    cargo_data = {
                        'nombre_cargo': nombre_cargo,
                        'nomenclatura': nomenclatura,
                        'nivel': nivel,
                        'naturaleza': naturaleza,
                        'asignacion_basica': asignacion_basica,
                        'prima_tecnica': prima_tecnica,
                        'dependencia': dependencia,
                        'ubicacion': ubicacion,
                        'jefe': jefes_options[jefe_index]['id'],
                        'decreto_creacion': decreto_creacion,
                        'estado': 'Activo',
                        'observaciones': observaciones,
                        'id_personalizado': id_personalizado if id_personalizado > 0 else None
                    }
                    
                    # Crear cargo
                    success, cargo_id = add_cargo(cargo_data)
                    
                    if success:
                        st.success(f"Cargo creado correctamente con ID: {cargo_id}")
                    else:
                        st.error(f"Error al crear el cargo: {cargo_id}")
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<h3 class="subsection-header">Importar Cargos</h3>', unsafe_allow_html=True)
            st.markdown('<p class="help-text">Suba un archivo Excel con los cargos a importar. El archivo debe contener al menos las columnas: nombre_cargo, nomenclatura, nivel, naturaleza, asignacion_basica</p>', unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader("Seleccione el archivo Excel", type=['xlsx', 'xls'])
            
            if uploaded_file is not None:
                if st.button("Procesar Archivo", use_container_width=True):
                    success, message = importar_excel(uploaded_file, 'cargos')
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        
        with col2:
            st.markdown('<h3 class="subsection-header">Exportar Cargos</h3>', unsafe_allow_html=True)
            
            if st.button("Exportar todos los cargos", use_container_width=True):
                cargos = get_all_cargos()
                
                if cargos:
                    excel_href = generate_excel(cargos, "cargos_completo")
                    st.markdown(excel_href, unsafe_allow_html=True)
                else:
                    st.info("No hay cargos para exportar")

# Página de gestión de servidores
def servidores_page():
    st.markdown('<h1 class="main-header">Gestión de Servidores</h1>', unsafe_allow_html=True)
    
    # Crear tabs para diferentes secciones
    tab1, tab2, tab3 = st.tabs(["Listar Servidores", "Nuevo Servidor", "Importar/Exportar"])
    
    with tab1:
        # Búsqueda y filtros
        buscar = st.text_input("Buscar por nombre, apellido o documento")
        
        # Obtener todos los servidores
        servidores = get_all_servidores()
        
        # Aplicar filtros
        servidores_filtrados = []
        for servidor in servidores:
            # Filtro de búsqueda
            if buscar and buscar.lower() not in servidor['nombres'].lower() and buscar.lower() not in servidor['apellidos'].lower() and buscar.lower() not in str(servidor['documento_identidad']).lower():
                continue
            
            servidores_filtrados.append(servidor)
        
        # Mostrar servidores
        if servidores_filtrados:
            # Convertir a dataframe para mostrar
            df_servidores = pd.DataFrame([{
                'ID': s['id'],
                'Documento': s['documento_identidad'],
                'Nombres': s['nombres'],
                'Apellidos': s['apellidos'],
                'Email': s['email'],
                'Teléfono': s['telefono'],
                'Estado': s['estado']
            } for s in servidores_filtrados])
            
            st.dataframe(df_servidores, use_container_width=True)
            
            # Seleccionar servidor para ver detalles o editar
            servidor_id = st.selectbox("Seleccionar servidor para ver detalles o editar", 
                                  [s['id'] for s in servidores_filtrados],
                                  format_func=lambda x: next((f"{s['nombres']} {s['apellidos']}" for s in servidores_filtrados if s['id'] == x), ''))
            
            if servidor_id:
                servidor_seleccionado = next((s for s in servidores_filtrados if s['id'] == servidor_id), None)
                
                if servidor_seleccionado:
                    with st.expander("Detalles del Servidor", expanded=True):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.text_input("Documento de Identidad", servidor_seleccionado['documento_identidad'], key="edit_documento_identidad")
                            st.selectbox("Tipo de Documento", 
                                       ["Cédula de Ciudadanía", "Cédula de Extranjería", "Pasaporte"],
                                       index=["Cédula de Ciudadanía", "Cédula de Extranjería", "Pasaporte"].index(servidor_seleccionado['tipo_documento']) if servidor_seleccionado['tipo_documento'] in ["Cédula de Ciudadanía", "Cédula de Extranjería", "Pasaporte"] else 0,
                                       key="edit_tipo_documento")
                            st.text_input("Nombres", servidor_seleccionado['nombres'], key="edit_nombres")
                            st.text_input("Apellidos", servidor_seleccionado['apellidos'], key="edit_apellidos")
                        
                        with col2:
                            st.text_input("Email", servidor_seleccionado['email'] if servidor_seleccionado['email'] else "", key="edit_email")
                            st.text_input("Teléfono", servidor_seleccionado['telefono'] if servidor_seleccionado['telefono'] else "", key="edit_telefono")
                            st.text_input("Dirección", servidor_seleccionado['direccion'] if servidor_seleccionado['direccion'] else "", key="edit_direccion")
                            st.selectbox("Estado", 
                                       ["Activo", "Inactivo", "Retirado"],
                                       index=["Activo", "Inactivo", "Retirado"].index(servidor_seleccionado['estado']) if servidor_seleccionado['estado'] in ["Activo", "Inactivo", "Retirado"] else 0,
                                       key="edit_estado_servidor")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            if st.button("Guardar Cambios", use_container_width=True):
                                # Preparar datos actualizados
                                servidor_actualizado = {
                                    'documento_identidad': st.session_state.edit_documento_identidad,
                                    'tipo_documento': st.session_state.edit_tipo_documento,
                                    'nombres': st.session_state.edit_nombres,
                                    'apellidos': st.session_state.edit_apellidos,
                                    'email': st.session_state.edit_email,
                                    'telefono': st.session_state.edit_telefono,
                                    'direccion': st.session_state.edit_direccion,
                                    'fecha_nacimiento': servidor_seleccionado['fecha_nacimiento'],
                                    'genero': servidor_seleccionado['genero'],
                                    'estado': st.session_state.edit_estado_servidor
                                }
                                
                                # Actualizar servidor
                                success, message = update_servidor(servidor_id, servidor_actualizado)
                                if success:
                                    st.success(message)
                                    st.experimental_rerun()
                                else:
                                    st.error(message)
                        
                        # Vinculaciones del servidor
                        st.markdown("---")
                        st.markdown('<h3 class="subsection-header">Vinculaciones del Servidor</h3>', unsafe_allow_html=True)
                        
                        vinculaciones = get_vinculaciones_by_servidor(servidor_id)
                        
                        if vinculaciones:
                            # Convertir a dataframe para mostrar
                            df_vinculaciones = pd.DataFrame([{
                                'ID': v['id'],
                                'Cargo': v['nombre_cargo'],
                                'Dependencia': v['dependencia'],
                                'Fecha Inicio': v['fecha_inicio'],
                                'Fecha Fin': v['fecha_fin'] if v['fecha_fin'] else "Actual",
                                'Tipo': v['tipo_vinculacion'],
                                'Resolución': v['resolucion_vinculacion']
                            } for v in vinculaciones])
                            
                            st.dataframe(df_vinculaciones, use_container_width=True)
                            
                            # Permitir añadir vinculación
                            if st.button("Nueva Vinculación", key="nueva_vinc_btn"):
                                st.session_state.page = 'vinculaciones'
                                st.session_state.servidor_seleccionado = servidor_id
                                st.experimental_rerun()
                        else:
                            st.info("Este servidor no tiene vinculaciones registradas")
                            
                            if st.button("Añadir Vinculación"):
                                st.session_state.page = 'vinculaciones'
                                st.session_state.servidor_seleccionado = servidor_id
                                st.experimental_rerun()
        else:
            st.info("No se encontraron servidores con los filtros seleccionados")
    
    with tab2:
        st.markdown('<h3 class="section-header">Registrar Nuevo Servidor</h3>', unsafe_allow_html=True)
        
        with st.form("nuevo_servidor_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                documento_identidad = st.text_input("Documento de Identidad", key="nuevo_documento_identidad")
                tipo_documento = st.selectbox("Tipo de Documento", 
                                            ["Cédula de Ciudadanía", "Cédula de Extranjería", "Pasaporte"],
                                            key="nuevo_tipo_documento")
                nombres = st.text_input("Nombres", key="nuevo_nombres")
                apellidos = st.text_input("Apellidos", key="nuevo_apellidos")
            
            with col2:
                email = st.text_input("Email", key="nuevo_email")
                telefono = st.text_input("Teléfono", key="nuevo_telefono")
                direccion = st.text_input("Dirección", key="nuevo_direccion")
                
                fecha_nacimiento = st.date_input("Fecha de Nacimiento", key="nuevo_fecha_nacimiento")
                genero = st.selectbox("Género", ["Masculino", "Femenino", "Otro"], key="nuevo_genero")
            
            submit = st.form_submit_button("Registrar Servidor", use_container_width=True)
            
            if submit:
                # Validar campos requeridos
                if not documento_identidad or not nombres or not apellidos:
                    st.error("Por favor, complete todos los campos requeridos")
                else:
                    # Preparar datos del nuevo servidor
                    servidor_data = {
                        'documento_identidad': documento_identidad,
                        'tipo_documento': tipo_documento,
                        'nombres': nombres,
                        'apellidos': apellidos,
                        'email': email,
                        'telefono': telefono,
                        'direccion': direccion,
                        'fecha_nacimiento': fecha_nacimiento.strftime('%Y-%m-%d'),
                        'genero': genero
                    }
                    
                    # Crear servidor
                    success, message = add_servidor(servidor_data)
                    
                    if success:
                        st.success(f"Servidor registrado correctamente con ID: {message}")
                        
                        # Preguntar si desea añadir una vinculación
                        if st.button("¿Desea añadir una vinculación para este servidor?"):
                            st.session_state.page = 'vinculaciones'
                            st.session_state.servidor_seleccionado = message
                            st.experimental_rerun()
                    else:
                        st.error(f"Error al registrar el servidor: {message}")
    
    with tab3:
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown('<h3 class="subsection-header">Importar Servidores</h3>', unsafe_allow_html=True)
            st.markdown('<p class="help-text">Suba un archivo Excel con los servidores a importar. El archivo debe contener al menos las columnas: documento_identidad, tipo_documento, nombres, apellidos</p>', unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader("Seleccione el archivo Excel", type=['xlsx', 'xls'], key="upload_servidores")
            
            if uploaded_file is not None:
                if st.button("Procesar Archivo", use_container_width=True, key="btn_procesar_servidores"):
                    success, message = importar_excel(uploaded_file, 'servidores')
                    
                    if success:
                        st.success(message)
                    else:
                        st.error(message)
        
        with col2:
            st.markdown('<h3 class="subsection-header">Exportar Servidores</h3>', unsafe_allow_html=True)
            
            if st.button("Exportar todos los servidores", use_container_width=True):
                servidores = get_all_servidores()
                
                if servidores:
                    excel_href = generate_excel(servidores, "servidores_completo")
                    st.markdown(excel_href, unsafe_allow_html=True)
                else:
                    st.info("No hay servidores para exportar")

# Página de vinculaciones
def vinculaciones_page():
    st.markdown('<h1 class="main-header">Gestión de Vinculaciones</h1>', unsafe_allow_html=True)
    
    # Verificar si viene de servidores
    servidor_preseleccionado = st.session_state.get('servidor_seleccionado', None)
    
    # Crear tabs para diferentes secciones
    tab1, tab2 = st.tabs(["Nueva Vinculación", "Historial de Vinculaciones"])
    
    with tab1:
        st.markdown('<h3 class="section-header">Registrar Nueva Vinculación</h3>', unsafe_allow_html=True)
        
        # Seleccionar servidor
        servidores = get_all_servidores()
        
        servidor_index = 0
        if servidor_preseleccionado:
            for i, s in enumerate(servidores):
                if s['id'] == servidor_preseleccionado:
                    servidor_index = i
                    break
        
        servidor_id = st.selectbox("Seleccionar Servidor", 
                               range(len(servidores)),
                               format_func=lambda i: f"{servidores[i]['documento_identidad']} - {servidores[i]['nombres']} {servidores[i]['apellidos']}",
                               index=servidor_index,
                               key="vinculacion_servidor_index")
        
        if servidor_id is not None:
            servidor_seleccionado = servidores[servidor_id]
            
            # Formulario de vinculación
            with st.form("nueva_vinculacion_form"):
                st.markdown(f"**Servidor:** {servidor_seleccionado['nombres']} {servidor_seleccionado['apellidos']}")
                
                # Obtener cargos disponibles
                cargos = get_all_cargos()
                
                cargo_id = st.selectbox("Seleccionar Cargo", 
                                     range(len(cargos)),
                                     format_func=lambda i: f"{cargos[i]['nombre_cargo']} - {cargos[i]['nomenclatura']} - {cargos[i]['dependencia']}",
                                     key="vinculacion_cargo_index")
                
                if cargo_id is not None:
                    cargo_seleccionado = cargos[cargo_id]
                    
                    st.markdown(f"**Asignación Básica:** ${cargo_seleccionado['asignacion_basica']:,.0f}")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fecha_inicio = st.date_input("Fecha de Inicio", key="vinculacion_fecha_inicio")
                        tipo_vinculacion = st.selectbox("Tipo de Vinculación", 
                                                     ["Nombramiento Ordinario", "Carrera Administrativa", "Provisionalidad", "Encargo", "Comisión"],
                                                     key="vinculacion_tipo")
                    
                    with col2:
                        fecha_fin = st.date_input("Fecha de Fin (dejar vacío para vinculación activa)", 
                                               value=None, 
                                               key="vinculacion_fecha_fin")
                        resolucion = st.text_input("Resolución de Vinculación", key="vinculacion_resolucion")
                    
                    acta_posesion = st.text_input("Acta de Posesión", key="vinculacion_acta_posesion")
                    observaciones = st.text_area("Observaciones", key="vinculacion_observaciones")
                    
                    submit = st.form_submit_button("Registrar Vinculación", use_container_width=True)
                    
                    if submit:
                        # Preparar datos de la vinculación
                        vinculacion_data = {
                            'servidor_id': servidor_seleccionado['id'],
                            'cargo_id': cargo_seleccionado['id'],
                            'fecha_inicio': fecha_inicio.strftime('%Y-%m-%d'),
                            'fecha_fin': fecha_fin.strftime('%Y-%m-%d') if fecha_fin else None,
                            'tipo_vinculacion': tipo_vinculacion,
                            'resolucion_vinculacion': resolucion,
                            'acta_posesion': acta_posesion,
                            'observaciones': observaciones
                        }
                        
                        # Crear vinculación
                        success, message = add_vinculacion(vinculacion_data)
                        
                        if success:
                            st.success(f"Vinculación registrada correctamente")
                            
                            # Limpiar la preselección
                            if 'servidor_seleccionado' in st.session_state:
                                del st.session_state.servidor_seleccionado
                                
                            st.experimental_rerun()
                        else:
                            st.error(f"Error al registrar la vinculación: {message}")
    
    with tab2:
        st.markdown('<h3 class="section-header">Historial de Vinculaciones</h3>', unsafe_allow_html=True)
        
        # Seleccionar servidor para ver historial
        servidor_hist_index = 0
        if servidor_preseleccionado:
            for i, s in enumerate(servidores):
                if s['id'] == servidor_preseleccionado:
                    servidor_hist_index = i
                    break
        
        servidor_hist_id = st.selectbox("Seleccionar Servidor", 
                                    range(len(servidores)),
                                    format_func=lambda i: f"{servidores[i]['documento_identidad']} - {servidores[i]['nombres']} {servidores[i]['apellidos']}",
                                    index=servidor_hist_index,
                                    key="vinculacion_hist_servidor_index")
        
        if servidor_hist_id is not None:
            servidor_hist = servidores[servidor_hist_id]
            
            # Obtener vinculaciones del servidor
            vinculaciones = get_vinculaciones_by_servidor(servidor_hist['id'])
            
            if vinculaciones:
                # Convertir a dataframe para mostrar
                df_vinculaciones = pd.DataFrame([{
                    'ID': v['id'],
                    'Cargo': v['nombre_cargo'],
                    'Dependencia': v['dependencia'],
                    'Fecha Inicio': v['fecha_inicio'],
                    'Fecha Fin': v['fecha_fin'] if v['fecha_fin'] else "Actual",
                    'Tipo': v['tipo_vinculacion'],
                    'Resolución': v['resolucion_vinculacion'],
                    'Acta Posesión': v['acta_posesion']
                } for v in vinculaciones])
                
                st.dataframe(df_vinculaciones, use_container_width=True)
                
                # Seleccionar vinculación para ver detalles
                vinculacion_id = st.selectbox("Seleccionar vinculación para ver detalles", 
                                          [v['id'] for v in vinculaciones],
                                          format_func=lambda x: next((f"{v['nombre_cargo']} ({v['fecha_inicio']} - {v['fecha_fin'] if v['fecha_fin'] else 'Actual'})" for v in vinculaciones if v['id'] == x), ''))
                
                if vinculacion_id:
                    vinculacion_seleccionada = next((v for v in vinculaciones if v['id'] == vinculacion_id), None)
                    
                    if vinculacion_seleccionada:
                        with st.expander("Detalles de la Vinculación", expanded=True):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown(f"**Cargo:** {vinculacion_seleccionada['nombre_cargo']}")
                                st.markdown(f"**Dependencia:** {vinculacion_seleccionada['dependencia']}")
                                st.markdown(f"**Fecha Inicio:** {vinculacion_seleccionada['fecha_inicio']}")
                                st.markdown(f"**Fecha Fin:** {vinculacion_seleccionada['fecha_fin'] if vinculacion_seleccionada['fecha_fin'] else 'Actual'}")
                            
                            with col2:
                                st.markdown(f"**Tipo de Vinculación:** {vinculacion_seleccionada['tipo_vinculacion']}")
                                st.markdown(f"**Resolución:** {vinculacion_seleccionada['resolucion_vinculacion']}")
                                st.markdown(f"**Acta de Posesión:** {vinculacion_seleccionada['acta_posesion']}")
                            
                            st.markdown(f"**Observaciones:** {vinculacion_seleccionada['observaciones']}")
                            
                            # Opción para editar vinculación
                            with st.form("editar_vinculacion_form"):
                                st.markdown("### Editar Vinculación")
                                
                                col1, col2 = st.columns(2)
                                
                                with col1:
                                    fecha_inicio_edit = st.date_input("Fecha de Inicio", 
                                                                  value=datetime.strptime(vinculacion_seleccionada['fecha_inicio'], '%Y-%m-%d'),
                                                                  key="edit_vinc_fecha_inicio")
                                    tipo_vinculacion_edit = st.selectbox("Tipo de Vinculación", 
                                                                      ["Nombramiento Ordinario", "Carrera Administrativa", "Provisionalidad", "Encargo", "Comisión"],
                                                                      index=["Nombramiento Ordinario", "Carrera Administrativa", "Provisionalidad", "Encargo", "Comisión"].index(vinculacion_seleccionada['tipo_vinculacion']) if vinculacion_seleccionada['tipo_vinculacion'] in ["Nombramiento Ordinario", "Carrera Administrativa", "Provisionalidad", "Encargo", "Comisión"] else 0,
                                                                      key="edit_vinc_tipo")
                                
                                with col2:
                                    fecha_fin_value = None
                                    if vinculacion_seleccionada['fecha_fin']:
                                        fecha_fin_value = datetime.strptime(vinculacion_seleccionada['fecha_fin'], '%Y-%m-%d')
                                    
                                    fecha_fin_edit = st.date_input("Fecha de Fin", 
                                                               value=fecha_fin_value,
                                                               key="edit_vinc_fecha_fin")
                                    resolucion_edit = st.text_input("Resolución de Vinculación", 
                                                                value=vinculacion_seleccionada['resolucion_vinculacion'] if vinculacion_seleccionada['resolucion_vinculacion'] else "",
                                                                key="edit_vinc_resolucion")
                                
                                acta_posesion_edit = st.text_input("Acta de Posesión", 
                                                              value=vinculacion_seleccionada['acta_posesion'] if vinculacion_seleccionada['acta_posesion'] else "",
                                                              key="edit_vinc_acta_posesion")
                                observaciones_edit = st.text_area("Observaciones", 
                                                             value=vinculacion_seleccionada['observaciones'] if vinculacion_seleccionada['observaciones'] else "",
                                                             key="edit_vinc_observaciones")
                                
                                submit_edit = st.form_submit_button("Guardar Cambios", use_container_width=True)
                                
                                if submit_edit:
                                    # Preparar datos actualizados
                                    vinculacion_actualizada = {
                                        'cargo_id': vinculacion_seleccionada['cargo_id'],
                                        'fecha_inicio': fecha_inicio_edit.strftime('%Y-%m-%d'),
                                        'fecha_fin': fecha_fin_edit.strftime('%Y-%m-%d') if fecha_fin_edit else None,
                                        'tipo_vinculacion': tipo_vinculacion_edit,
                                        'resolucion_vinculacion': resolucion_edit,
                                        'acta_posesion': acta_posesion_edit,
                                        'observaciones': observaciones_edit
                                    }
                                    
                                    # Actualizar vinculación
                                    if update_vinculacion(vinculacion_id, vinculacion_actualizada):
                                        st.success("Vinculación actualizada correctamente")
                                        st.experimental_rerun()
                                    else:
                                        st.error("Error al actualizar la vinculación")
                            
                            # Opción para registrar traslado
                            if not vinculacion_seleccionada['fecha_fin']:
                                if st.button("Registrar Traslado", use_container_width=True):
                                    st.session_state.page = 'traslados'
                                    st.session_state.vinculacion_seleccionada = vinculacion_id
                                    st.experimental_rerun()
            else:
                st.info("Este servidor no tiene vinculaciones registradas")

# Página de traslados 
def traslados_page():
    st.markdown('<h1 class="main-header">Gestión de Traslados</h1>', unsafe_allow_html=True)
    
    # Verificar si viene de vinculaciones
    vinculacion_preseleccionada = st.session_state.get('vinculacion_seleccionada', None)
    
    # Crear tabs para diferentes secciones
    tab1, tab2 = st.tabs(["Nuevo Traslado", "Historial de Traslados"])
    
    with tab1:
        st.markdown('<h3 class="section-header">Registrar Nuevo Traslado</h3>', unsafe_allow_html=True)
        
        # Primero seleccionar el servidor
        servidores = get_all_servidores()
        
        servidor_id = st.selectbox("Seleccionar Servidor", 
                               range(len(servidores)),
                               format_func=lambda i: f"{servidores[i]['documento_identidad']} - {servidores[i]['nombres']} {servidores[i]['apellidos']}",
                               key="traslado_servidor_index")
        
        if servidor_id is not None:
            servidor_seleccionado = servidores[servidor_id]
            
            # Obtener vinculaciones activas del servidor
            vinculaciones = get_vinculaciones_by_servidor(servidor_seleccionado['id'])
            vinculaciones_activas = [v for v in vinculaciones if not v['fecha_fin']]
            
            if vinculaciones_activas:
                vinculacion_index = 0
                
                if vinculacion_preseleccionada:
                    for i, v in enumerate(vinculaciones_activas):
                        if v['id'] == vinculacion_preseleccionada:
                            vinculacion_index = i
                            break
                
                vinculacion_id = st.selectbox("Seleccionar Vinculación Activa", 
                                          range(len(vinculaciones_activas)),
                                          format_func=lambda i: f"{vinculaciones_activas[i]['nombre_cargo']} - {vinculaciones_activas[i]['dependencia']} (desde {vinculaciones_activas[i]['fecha_inicio']})",
                                          index=vinculacion_index,
                                          key="traslado_vinculacion_index")
                
                if vinculacion_id is not None:
                    vinculacion_seleccionada = vinculaciones_activas[vinculacion_id]
                    
                    # Formulario de traslado
                    with st.form("nuevo_traslado_form"):
                        st.markdown(f"**Servidor:** {servidor_seleccionado['nombres']} {servidor_seleccionado['apellidos']}")
                        st.markdown(f"**Cargo Actual:** {vinculacion_seleccionada['nombre_cargo']} - {vinculacion_seleccionada['dependencia']}")
                        
                        # Obtener cargos disponibles para traslado
                        cargos = get_all_cargos()
                        cargos_disponibles = [c for c in cargos if c['id'] != vinculacion_seleccionada['cargo_id']]
                        
                        cargo_destino_id = st.selectbox("Seleccionar Cargo Destino", 
                                                     range(len(cargos_disponibles)),
                                                     format_func=lambda i: f"{cargos_disponibles[i]['nombre_cargo']} - {cargos_disponibles[i]['nomenclatura']} - {cargos_disponibles[i]['dependencia']}",
                                                     key="traslado_cargo_destino_index")
                        
                        if cargo_destino_id is not None:
                            cargo_destino = cargos_disponibles[cargo_destino_id]
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                fecha_traslado = st.date_input("Fecha de Traslado", key="traslado_fecha")
                                resolucion_traslado = st.text_input("Resolución de Traslado", key="traslado_resolucion")
                            
                            with col2:
                                motivo_traslado = st.selectbox("Motivo del Traslado", 
                                                            ["Necesidad del servicio", "Solicitud del servidor", "Reestructuración", "Otro"],
                                                            key="traslado_motivo")
                            
                            observaciones = st.text_area("Observaciones", key="traslado_observaciones")
                            
                            submit = st.form_submit_button("Registrar Traslado", use_container_width=True)
                            
                            if submit:
                                # Preparar datos del traslado
                                traslado_data = {
                                    'vinculacion_id': vinculacion_seleccionada['id'],
                                    'cargo_origen_id': vinculacion_seleccionada['cargo_id'],
                                    'cargo_destino_id': cargo_destino['id'],
                                    'fecha_traslado': fecha_traslado.strftime('%Y-%m-%d'),
                                    'resolucion_traslado': resolucion_traslado,
                                    'motivo_traslado': motivo_traslado,
                                    'observaciones': observaciones
                                }
                                
                                # Crear traslado
                                if add_traslado(traslado_data):
                                    st.success("Traslado registrado correctamente")
                                    
                                    # Limpiar la preselección
                                    if 'vinculacion_seleccionada' in st.session_state:
                                        del st.session_state.vinculacion_seleccionada
                                    
                                    st.experimental_rerun()
                                else:
                                    st.error("Error al registrar el traslado")
            else:
                st.error("El servidor seleccionado no tiene vinculaciones activas")
    
    with tab2:
        st.markdown('<h3 class="section-header">Historial de Traslados</h3>', unsafe_allow_html=True)
        
        # Seleccionar servidor para ver historial
        servidor_hist_id = st.selectbox("Seleccionar Servidor", 
                                    range(len(servidores)),
                                    format_func=lambda i: f"{servidores[i]['documento_identidad']} - {servidores[i]['nombres']} {servidores[i]['apellidos']}",
                                    key="traslado_hist_servidor_index")
        
        if servidor_hist_id is not None:
            servidor_hist = servidores[servidor_hist_id]
            
            # Obtener vinculaciones del servidor
            vinculaciones = get_vinculaciones_by_servidor(servidor_hist['id'])
            
            if vinculaciones:
                # Seleccionar vinculación para ver sus traslados
                vinculacion_hist_id = st.selectbox("Seleccionar Vinculación", 
                                               [v['id'] for v in vinculaciones],
                                               format_func=lambda x: next((f"{v['nombre_cargo']} ({v['fecha_inicio']} - {v['fecha_fin'] if v['fecha_fin'] else 'Actual'})" for v in vinculaciones if v['id'] == x), ''),
                                               key="traslado_hist_vinculacion_id")
                
                if vinculacion_hist_id:
                    # Obtener traslados de esta vinculación
                    traslados = get_traslados_by_vinculacion(vinculacion_hist_id)
                    
                    if traslados:
                        # Convertir a dataframe para mostrar
                        df_traslados = pd.DataFrame([{
                            'ID': t['id'],
                            'Fecha': t['fecha_traslado'],
                            'Cargo Origen': t['cargo_origen_nombre'],
                            'Cargo Destino': t['cargo_destino_nombre'],
                            'Resolución': t['resolucion_traslado'],
                            'Motivo': t['motivo_traslado']
                        } for t in traslados])
                        
                        st.dataframe(df_traslados, use_container_width=True)
                        
                        # Seleccionar traslado para ver detalles
                        traslado_id = st.selectbox("Seleccionar traslado para ver detalles", 
                                               [t['id'] for t in traslados],
                                               format_func=lambda x: next((f"Traslado del {t['fecha_traslado']}: {t['cargo_origen_nombre']} → {t['cargo_destino_nombre']}" for t in traslados if t['id'] == x), ''))
                        
                        if traslado_id:
                            traslado_seleccionado = next((t for t in traslados if t['id'] == traslado_id), None)
                            
                            if traslado_seleccionado:
                                with st.expander("Detalles del Traslado", expanded=True):
                                    col1, col2 = st.columns(2)
                                    
                                    with col1:
                                        st.markdown(f"**Fecha de Traslado:** {traslado_seleccionado['fecha_traslado']}")
                                        st.markdown(f"**Cargo Origen:** {traslado_seleccionado['cargo_origen_nombre']}")
                                        st.markdown(f"**Cargo Destino:** {traslado_seleccionado['cargo_destino_nombre']}")
                                    
                                    with col2:
                                        st.markdown(f"**Resolución:** {traslado_seleccionado['resolucion_traslado']}")
                                        st.markdown(f"**Motivo:** {traslado_seleccionado['motivo_traslado']}")
                                    
                                    st.markdown(f"**Observaciones:** {traslado_seleccionado['observaciones']}")
                    else:
                        st.info("Esta vinculación no tiene traslados registrados")
            else:
                st.info("Este servidor no tiene vinculaciones registradas")

# Página de certificaciones
def certificaciones_page():
    st.markdown('<h1 class="main-header">Generación de Certificaciones</h1>', unsafe_allow_html=True)
    
    # Crear tabs para diferentes tipos de certificaciones
    tab1, tab2 = st.tabs(["Certificación Laboral", "Certificación de Historial"])
    
    with tab1:
        st.markdown('<h3 class="section-header">Generar Certificación Laboral</h3>', unsafe_allow_html=True)
        
        # Seleccionar servidor
        servidores = get_all_servidores()
        
        servidor_id = st.selectbox("Seleccionar Servidor", 
                               range(len(servidores)),
                               format_func=lambda i: f"{servidores[i]['documento_identidad']} - {servidores[i]['nombres']} {servidores[i]['apellidos']}",
                               key="cert_servidor_index")
        
        if servidor_id is not None:
            servidor_seleccionado = servidores[servidor_id]
            
            # Formulario para la certificación
            with st.form("certificacion_form"):
                st.markdown(f"**Servidor:** {servidor_seleccionado['nombres']} {servidor_seleccionado['apellidos']}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    fecha_inicio = st.date_input("Fecha de Inicio", key="cert_fecha_inicio")
                
                with col2:
                    fecha_fin = st.date_input("Fecha de Fin", key="cert_fecha_fin")
                
                submit = st.form_submit_button("Generar Certificación", use_container_width=True)
                
                if submit:
                    # Validar fechas
                    if fecha_inicio > fecha_fin:
                        st.error("La fecha de inicio debe ser anterior a la fecha de fin")
                    else:
                        # Generar certificación
                        certificacion, error = generar_certificacion_laboral(
                            servidor_seleccionado['id'],
                            fecha_inicio.strftime('%Y-%m-%d'),
                            fecha_fin.strftime('%Y-%m-%d')
                        )
                        
                        if error:
                            st.error(error)
                        else:
                            # Mostrar la certificación
                            with st.expander("Certificación Laboral", expanded=True):
                                st.markdown(f"""
                                # CERTIFICACIÓN LABORAL
                                
                                **Fecha de Expedición:** {certificacion['fecha_generacion']}
                                
                                El suscrito jefe de la Oficina de Talento Humano certifica que:
                                
                                **{certificacion['servidor']['nombres']} {certificacion['servidor']['apellidos']}**
                                
                                Identificado(a) con {certificacion['servidor']['tipo_documento']} No. {certificacion['servidor']['documento_identidad']}, ha prestado/presta sus servicios en nuestra entidad, de acuerdo con la siguiente información:
                                """)
                                
                                # Mostrar vinculaciones
                                for i, v in enumerate(certificacion['vinculaciones']):
                                    st.markdown(f"""
                                    ### Vinculación {i+1}
                                    
                                    **Cargo:** {v['nombre_cargo']}  
                                    **Dependencia:** {v['dependencia']}  
                                    **Nivel:** {v['nivel']}  
                                    **Asignación Básica:** ${float(v['asignacion_basica']):,.0f}  
                                    **Periodo:** Del {v['fecha_inicio']} al {v['fecha_fin'] if v['fecha_fin'] else 'Actual'}  
                                    **Tipo de Vinculación:** {v['tipo_vinculacion']}  
                                    """)
                                
                                st.markdown("""
                                La presente certificación se expide a solicitud del interesado.
                                
                                Atentamente,
                                
                                
                                **Jefe de Talento Humano**
                                """)
                            
                            # Opción para exportar
                            if st.button("Exportar Certificación a PDF"):
                                st.info("Funcionalidad de exportación a PDF no implementada en este prototipo")
    
    with tab2:
        st.markdown('<h3 class="section-header">Certificación de Historial de Cargos</h3>', unsafe_allow_html=True)
        
        # Seleccionar servidor
        servidor_hist_id = st.selectbox("Seleccionar Servidor", 
                                    range(len(servidores)),
                                    format_func=lambda i: f"{servidores[i]['documento_identidad']} - {servidores[i]['nombres']} {servidores[i]['apellidos']}",
                                    key="cert_hist_servidor_index")
        
        if servidor_hist_id is not None:
            servidor_hist = servidores[servidor_hist_id]
            
            # Obtener vinculaciones del servidor
            vinculaciones = get_vinculaciones_by_servidor(servidor_hist['id'])
            
            if vinculaciones:
                # Mostrar historial completo
                st.markdown("### Historial Completo de Cargos")
                
                # Convertir a dataframe para mostrar
                df_vinculaciones = pd.DataFrame([{
                    'Cargo': v['nombre_cargo'],
                    'Dependencia': v['dependencia'],
                    'Fecha Inicio': v['fecha_inicio'],
                    'Fecha Fin': v['fecha_fin'] if v['fecha_fin'] else "Actual",
                    'Tipo': v['tipo_vinculacion']
                } for v in vinculaciones])
                
                st.dataframe(df_vinculaciones, use_container_width=True)
                
                # Generar certificación
                if st.button("Generar Certificación de Historial"):
                    with st.expander("Certificación de Historial de Cargos", expanded=True):
                        st.markdown(f"""
                        # CERTIFICACIÓN DE HISTORIAL DE CARGOS
                        
                        **Fecha de Expedición:** {datetime.now().strftime('%Y-%m-%d')}
                        
                        El suscrito jefe de la Oficina de Talento Humano certifica que:
                        
                        **{servidor_hist['nombres']} {servidor_hist['apellidos']}**
                        
                        Identificado(a) con {servidor_hist['tipo_documento']} No. {servidor_hist['documento_identidad']}, ha desempeñado los siguientes cargos en nuestra entidad:
                        """)
                        
                        # Mostrar vinculaciones en orden cronológico
                        vinculaciones_ordenadas = sorted(vinculaciones, key=lambda x: x['fecha_inicio'])
                        
                        for i, v in enumerate(vinculaciones_ordenadas):
                            st.markdown(f"""
                            ### {i+1}. {v['nombre_cargo']}
                            
                            **Dependencia:** {v['dependencia']}  
                            **Periodo:** Del {v['fecha_inicio']} al {v['fecha_fin'] if v['fecha_fin'] else 'Actual'}  
                            **Tipo de Vinculación:** {v['tipo_vinculacion']}  
                            **Asignación Básica:** ${float(v['asignacion_basica']):,.0f}  
                            """)
                        
                        st.markdown("""
                        La presente certificación se expide a solicitud del interesado.
                        
                        Atentamente,
                        
                        
                        **Jefe de Talento Humano**
                        """)
                    
                    # Opción para exportar
                    if st.button("Exportar Certificación de Historial a PDF"):
                        st.info("Funcionalidad de exportación a PDF no implementada en este prototipo")
            else:
                st.info("Este servidor no tiene vinculaciones registradas")

# Página de reportes
def reportes_page():
    st.markdown('<h1 class="main-header">Reportes y Estadísticas</h1>', unsafe_allow_html=True)
    
    # Crear tabs para diferentes tipos de reportes
    tab1, tab2, tab3, tab4 = st.tabs(["Cargos Vacantes", "Distribución de Personal", "Histórico de Vinculaciones", "Estadísticas Generales"])
    
    with tab1:
        st.markdown('<h3 class="section-header">Reporte de Cargos Vacantes</h3>', unsafe_allow_html=True)
        
        # Obtener cargos vacantes
        cargos_vacantes = buscar_cargos_vacantes()
        
        if cargos_vacantes:
            # Filtros
            col1, col2 = st.columns(2)
            
            with col1:
                nivel_filter = st.selectbox(
                    "Filtrar por nivel",
                    ["Todos", "Directivo", "Asesor", "Profesional", "Técnico", "Asistencial"],
                    key="vacantes_nivel_filter"
                )
            
            with col2:
                dependencia_filter = st.selectbox(
                    "Filtrar por dependencia",
                    ["Todas"] + list(set([c['dependencia'] for c in cargos_vacantes if c['dependencia']])),
                    key="vacantes_dependencia_filter"
                )
            
            # Aplicar filtros
            cargos_filtrados = []
            for cargo in cargos_vacantes:
                # Filtro de nivel
                if nivel_filter != "Todos" and cargo['nivel'] != nivel_filter:
                    continue
                
                # Filtro de dependencia
                if dependencia_filter != "Todas" and cargo['dependencia'] != dependencia_filter:
                    continue
                
                cargos_filtrados.append(cargo)
            
            # Mostrar resultados
            if cargos_filtrados:
                # Convertir a dataframe para mostrar
                df_vacantes = pd.DataFrame([{
                    'ID': c['id'],
                    'Cargo': c['nombre_cargo'],
                    'Nomenclatura': c['nomenclatura'],
                    'Nivel': c['nivel'],
                    'Naturaleza': c['naturaleza'],
                    'Asignación Básica': f"${float(c['asignacion_basica']):,.0f}",
                    'Dependencia': c['dependencia']
                } for c in cargos_filtrados])
                
                st.dataframe(df_vacantes, use_container_width=True)
                
                # Opción para exportar
                if st.button("Exportar Reporte de Cargos Vacantes", key="export_vacantes"):
                    excel_href = generate_excel(cargos_filtrados, "cargos_vacantes")
                    st.markdown(excel_href, unsafe_allow_html=True)
            else:
                st.info("No se encontraron cargos vacantes con los filtros seleccionados")
        else:
            st.info("No hay cargos vacantes actualmente")
    
    with tab2:
        st.markdown('<h3 class="section-header">Distribución de Personal</h3>', unsafe_allow_html=True)
        
        # Obtener estadísticas
        stats = obtener_estadisticas()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Por Nivel")
            
            if stats['niveles']:
                df_niveles = pd.DataFrame(stats['niveles'])
                st.bar_chart(df_niveles.set_index('nivel')['cantidad'])
                
                # Mostrar tabla con detalles
                st.dataframe(df_niveles, use_container_width=True)
            else:
                st.info("No hay datos para mostrar")
        
        with col2:
            st.markdown("### Por Naturaleza del Cargo")
            
            if stats['naturaleza']:
                df_naturaleza = pd.DataFrame(stats['naturaleza'])
                st.bar_chart(df_naturaleza.set_index('naturaleza')['cantidad'])
                
                # Mostrar tabla con detalles
                st.dataframe(df_naturaleza, use_container_width=True)
            else:
                st.info("No hay datos para mostrar")
        
        st.markdown("### Por Dependencia")
        
        if stats['dependencias']:
            df_dependencias = pd.DataFrame(stats['dependencias'])
            st.bar_chart(df_dependencias.set_index('dependencia')['cantidad'])
            
            # Mostrar tabla con detalles
            st.dataframe(df_dependencias, use_container_width=True)
        else:
            st.info("No hay datos para mostrar")
        
        # Opción para exportar
        if st.button("Exportar Informe de Distribución de Personal"):
            # Preparar datos para exportar
            export_data = {
                'niveles': stats['niveles'],
                'naturaleza': stats['naturaleza'],
                'dependencias': stats['dependencias']
            }
            
            excel_href = generate_excel(export_data, "distribucion_personal")
            st.markdown(excel_href, unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<h3 class="section-header">Histórico de Vinculaciones</h3>', unsafe_allow_html=True)
        
        # Formulario para filtrar por periodo
        col1, col2, col3 = st.columns(3)
        
        with col1:
            fecha_inicio = st.date_input("Fecha de Inicio", value=datetime(datetime.now().year-1, 1, 1), key="hist_fecha_inicio")
        
        with col2:
            fecha_fin = st.date_input("Fecha de Fin", key="hist_fecha_fin")
        
        with col3:
            tipo_vinculacion = st.selectbox(
                "Tipo de Vinculación",
                ["Todas", "Nombramiento Ordinario", "Carrera Administrativa", "Provisionalidad", "Encargo", "Comisión"],
                key="hist_tipo_vinculacion"
            )
        
        if st.button("Generar Reporte", key="btn_generar_hist"):
            # Conectar a la base de datos
            conn = get_db_connection()
            
            # Construir la consulta base
            query = '''
                SELECT v.*, s.nombres, s.apellidos, s.documento_identidad, c.nombre_cargo, c.nomenclatura, c.nivel, c.dependencia
                FROM vinculaciones v
                JOIN servidores s ON v.servidor_id = s.id
                JOIN cargos c ON v.cargo_id = c.id
                WHERE (v.fecha_inicio BETWEEN ? AND ?) OR (v.fecha_fin BETWEEN ? AND ?) OR (v.fecha_inicio <= ? AND (v.fecha_fin >= ? OR v.fecha_fin IS NULL))
            '''
            
            params = [
                fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d'),
                fecha_inicio.strftime('%Y-%m-%d'), fecha_fin.strftime('%Y-%m-%d'),
                fecha_fin.strftime('%Y-%m-%d'), fecha_inicio.strftime('%Y-%m-%d')
            ]
            
            # Aplicar filtro de tipo de vinculación si es necesario
            if tipo_vinculacion != "Todas":
                query += " AND v.tipo_vinculacion = ?"
                params.append(tipo_vinculacion)
            
            # Ejecutar la consulta
            vinculaciones = conn.execute(query, params).fetchall()
            conn.close()
            
            if vinculaciones:
                # Convertir a dataframe para mostrar
                df_vinculaciones = pd.DataFrame([{
                    'ID': v['id'],
                    'Servidor': f"{v['nombres']} {v['apellidos']}",
                    'Documento': v['documento_identidad'],
                    'Cargo': v['nombre_cargo'],
                    'Nivel': v['nivel'],
                    'Dependencia': v['dependencia'],
                    'Fecha Inicio': v['fecha_inicio'],
                    'Fecha Fin': v['fecha_fin'] if v['fecha_fin'] else "Actual",
                    'Tipo': v['tipo_vinculacion'],
                    'Resolución': v['resolucion_vinculacion'],
                    'Acta Posesión': v['acta_posesion']
                } for v in vinculaciones])
                
                st.dataframe(df_vinculaciones, use_container_width=True)
                
                # Estadísticas del reporte
                st.markdown("### Estadísticas del Reporte")
                
                vinc_por_tipo = {}
                for v in vinculaciones:
                    tipo = v['tipo_vinculacion']
                    vinc_por_tipo[tipo] = vinc_por_tipo.get(tipo, 0) + 1
                
                df_tipos = pd.DataFrame([{"Tipo": k, "Cantidad": v} for k, v in vinc_por_tipo.items()])
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Total de vinculaciones:** {len(vinculaciones)}")
                    st.markdown(f"**Periodo:** Del {fecha_inicio.strftime('%Y-%m-%d')} al {fecha_fin.strftime('%Y-%m-%d')}")
                
                with col2:
                    st.markdown("#### Vinculaciones por Tipo")
                    st.dataframe(df_tipos, use_container_width=True)
                
                # Opción para exportar
                if st.button("Exportar Histórico de Vinculaciones"):
                    export_data = [dict(v) for v in vinculaciones]
                    excel_href = generate_excel(export_data, "historico_vinculaciones")
                    st.markdown(excel_href, unsafe_allow_html=True)
            else:
                st.info("No se encontraron vinculaciones en el periodo seleccionado")
    
    with tab4:
        st.markdown('<h3 class="section-header">Estadísticas Generales</h3>', unsafe_allow_html=True)
        
        # Obtener estadísticas
        stats = obtener_estadisticas()
        
        # Mostrar estadísticas en tarjetas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(label="Total de Cargos", value=stats['total_cargos'])
        
        with col2:
            st.metric(label="Servidores Activos", value=stats['total_servidores'])
        
        with col3:
            st.metric(label="Cargos Vacantes", value=stats['cargos_vacantes'])
            
            st.markdown(f"**Tasa de Ocupación:** {((stats['total_cargos'] - stats['cargos_vacantes']) / stats['total_cargos'] * 100):.1f}%")
        
        # Gráfico de ocupación
        ocupacion_data = {
            'Estado': ['Ocupados', 'Vacantes'],
            'Cantidad': [stats['total_cargos'] - stats['cargos_vacantes'], stats['cargos_vacantes']]
        }
        
        df_ocupacion = pd.DataFrame(ocupacion_data)
        
        st.markdown("### Ocupación de Cargos")
        st.bar_chart(df_ocupacion.set_index('Estado'))
        
        # Información adicional
        conn = get_db_connection()
        
        # Vinculaciones por año
        vinculaciones_por_anio = conn.execute('''
            SELECT strftime('%Y', fecha_inicio) as año, COUNT(*) as cantidad
            FROM vinculaciones
            GROUP BY strftime('%Y', fecha_inicio)
            ORDER BY año
        ''').fetchall()
        
        # Traslados por año
        traslados_por_anio = conn.execute('''
            SELECT strftime('%Y', fecha_traslado) as año, COUNT(*) as cantidad
            FROM traslados
            GROUP BY strftime('%Y', fecha_traslado)
            ORDER BY año
        ''').fetchall()
        
        conn.close()
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Vinculaciones por Año")
            
            if vinculaciones_por_anio:
                df_vinc_anio = pd.DataFrame([{"Año": v['año'], "Cantidad": v['cantidad']} for v in vinculaciones_por_anio])
                st.bar_chart(df_vinc_anio.set_index('Año'))
                st.dataframe(df_vinc_anio, use_container_width=True)
            else:
                st.info("No hay datos para mostrar")
        
        with col2:
            st.markdown("### Traslados por Año")
            
            if traslados_por_anio:
                df_traslados_anio = pd.DataFrame([{"Año": t['año'], "Cantidad": t['cantidad']} for t in traslados_por_anio])
                st.bar_chart(df_traslados_anio.set_index('Año'))
                st.dataframe(df_traslados_anio, use_container_width=True)
            else:
                st.info("No hay datos para mostrar")
        
        # Opción para exportar
        if st.button("Exportar Informe de Estadísticas Generales"):
            # Preparar datos para exportar
            export_data = {
                'resumen': {
                    'total_cargos': stats['total_cargos'],
                    'servidores_activos': stats['total_servidores'],
                    'cargos_vacantes': stats['cargos_vacantes'],
                    'tasa_ocupacion': (stats['total_cargos'] - stats['cargos_vacantes']) / stats['total_cargos'] * 100
                },
                'por_nivel': stats['niveles'],
                'por_naturaleza': stats['naturaleza'],
                'por_dependencia': stats['dependencias'],
                'vinculaciones_por_anio': [dict(v) for v in vinculaciones_por_anio],
                'traslados_por_anio': [dict(t) for t in traslados_por_anio]
            }
            
            excel_href = generate_excel(export_data, "estadisticas_generales")
            st.markdown(excel_href, unsafe_allow_html=True)

# Página de configuración
def configuracion_page():
    st.markdown('<h1 class="main-header">Configuración del Sistema</h1>', unsafe_allow_html=True)
    
    # Verificar si el usuario tiene permisos de administrador
    if st.session_state.user['rol'] != 'admin':
        st.error("No tiene permisos para acceder a esta sección")
        return
    
    # Crear tabs para diferentes secciones de configuración
    tab1, tab2, tab3 = st.tabs(["Dependencias", "Importar/Exportar Base de Datos", "Configuración General"])
    
    with tab1:
        st.markdown('<h3 class="section-header">Gestión de Dependencias</h3>', unsafe_allow_html=True)
        
        # Obtener todas las dependencias
        dependencias = get_all_dependencias()
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Lista de dependencias
            st.markdown("### Dependencias Existentes")
            
            if dependencias:
                # Convertir a dataframe para mostrar
                df_dependencias = pd.DataFrame([{
                    'ID': d['id'],
                    'Nombre': d['nombre'],
                    'Código': d['codigo'],
                    'Descripción': d['descripcion']
                } for d in dependencias])
                
                st.dataframe(df_dependencias, use_container_width=True)
                
                # Seleccionar dependencia para editar
                dependencia_id = st.selectbox("Seleccionar dependencia para editar", 
                                         [d['id'] for d in dependencias],
                                         format_func=lambda x: next((d['nombre'] for d in dependencias if d['id'] == x), ''))
                
                if dependencia_id:
                    dependencia_seleccionada = next((d for d in dependencias if d['id'] == dependencia_id), None)
                    
                    if dependencia_seleccionada:
                        with st.form("editar_dependencia_form"):
                            st.text_input("Nombre", dependencia_seleccionada['nombre'], key="edit_dep_nombre")
                            st.text_input("Código", dependencia_seleccionada['codigo'], key="edit_dep_codigo")
                            st.text_area("Descripción", dependencia_seleccionada['descripcion'] if dependencia_seleccionada['descripcion'] else "", key="edit_dep_descripcion")
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                submit_edit = st.form_submit_button("Guardar Cambios", use_container_width=True)
                            
                            with col2:
                                delete_btn = st.form_submit_button("Eliminar Dependencia", use_container_width=True)
                            
                            if submit_edit:
                                # Conectar a la base de datos
                                conn = get_db_connection()
                                
                                try:
                                    conn.execute('''
                                        UPDATE dependencias 
                                        SET nombre = ?, codigo = ?, descripcion = ? 
                                        WHERE id = ?
                                    ''', (
                                        st.session_state.edit_dep_nombre,
                                        st.session_state.edit_dep_codigo,
                                        st.session_state.edit_dep_descripcion,
                                        dependencia_id
                                    ))
                                    
                                    conn.commit()
                                    conn.close()
                                    
                                    st.success("Dependencia actualizada correctamente")
                                    st.experimental_rerun()
                                except sqlite3.IntegrityError as e:
                                    conn.close()
                                    if "UNIQUE constraint failed: dependencias.nombre" in str(e):
                                        st.error("Ya existe una dependencia con ese nombre")
                                    elif "UNIQUE constraint failed: dependencias.codigo" in str(e):
                                        st.error("Ya existe una dependencia con ese código")
                                    else:
                                        st.error(str(e))
                            
                            if delete_btn:
                                # Verificar si hay cargos asociados a esta dependencia
                                conn = get_db_connection()
                                cargos_asociados = conn.execute(
                                    "SELECT COUNT(*) FROM cargos WHERE dependencia = ?", 
                                    (dependencia_seleccionada['nombre'],)
                                ).fetchone()[0]
                                
                                if cargos_asociados > 0:
                                    conn.close()
                                    st.error(f"No se puede eliminar la dependencia porque tiene {cargos_asociados} cargos asociados")
                                else:
                                    conn.execute("DELETE FROM dependencias WHERE id = ?", (dependencia_id,))
                                    conn.commit()
                                    conn.close()
                                    
                                    st.success("Dependencia eliminada correctamente")
                                    st.experimental_rerun()
            else:
                st.info("No hay dependencias registradas")
        
        with col2:
            # Formulario para añadir nueva dependencia
            st.markdown("### Añadir Nueva Dependencia")
            
            with st.form("nueva_dependencia_form"):
                st.text_input("Nombre", key="nueva_dep_nombre")
                st.text_input("Código", key="nueva_dep_codigo")
                st.text_area("Descripción", key="nueva_dep_descripcion")
                
                submit = st.form_submit_button("Crear Dependencia", use_container_width=True)
                
                if submit:
                    # Validar campos requeridos
                    if not st.session_state.nueva_dep_nombre or not st.session_state.nueva_dep_codigo:
                        st.error("Nombre y código son campos requeridos")
                    else:
                        # Conectar a la base de datos
                        conn = get_db_connection()
                        
                        try:
                            conn.execute('''
                                INSERT INTO dependencias (nombre, codigo, descripcion, fecha_creacion)
                                VALUES (?, ?, ?, ?)
                            ''', (
                                st.session_state.nueva_dep_nombre,
                                st.session_state.nueva_dep_codigo,
                                st.session_state.nueva_dep_descripcion,
                                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            ))
                            
                            conn.commit()
                            conn.close()
                            
                            st.success("Dependencia creada correctamente")
                            st.experimental_rerun()
                        except sqlite3.IntegrityError as e:
                            conn.close()
                            if "UNIQUE constraint failed: dependencias.nombre" in str(e):
                                st.error("Ya existe una dependencia con ese nombre")
                            elif "UNIQUE constraint failed: dependencias.codigo" in str(e):
                                st.error("Ya existe una dependencia con ese código")
                            else:
                                st.error(str(e))
    
    with tab2:
        st.markdown('<h3 class="section-header">Importar/Exportar Base de Datos</h3>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Exportar Base de Datos")
            st.markdown('<p class="help-text">Esta opción permite realizar una copia de seguridad de toda la base de datos del sistema.</p>', unsafe_allow_html=True)
            
            if st.button("Exportar Base de Datos Completa", use_container_width=True):
                # En un sistema real, aquí se implementaría la exportación de la base de datos
                st.info("En un entorno de producción, esta función exportaría toda la base de datos SQLite a un archivo descargable.")
                st.success("Funcionalidad de exportación simulada correctamente")
        
        with col2:
            st.markdown("### Importar Base de Datos")
            st.markdown('<p class="help-text">Esta opción permite restaurar una copia de seguridad. PRECAUCIÓN: Esto sobrescribirá todos los datos actuales.</p>', unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader("Seleccione el archivo de base de datos", type=['db', 'sqlite'])
            
            if uploaded_file is not None:
                if st.button("Restaurar Base de Datos", use_container_width=True):
                    # En un sistema real, aquí se implementaría la importación de la base de datos
                    st.warning("ATENCIÓN: Esta acción sobrescribirá todos los datos existentes.")
                    
                    if st.button("Confirmar Restauración"):
                        st.info("En un entorno de producción, esta función restauraría la base de datos desde el archivo subido.")
                        st.success("Funcionalidad de importación simulada correctamente")
    
    with tab3:
        st.markdown('<h3 class="section-header">Configuración General del Sistema</h3>', unsafe_allow_html=True)
        
        # Estas serían las opciones de configuración generales del sistema
        with st.form("config_general_form"):
            st.markdown("### Opciones Generales")
            
            nombre_entidad = st.text_input("Nombre de la Entidad", value="Agencia Nacional", key="config_nombre_entidad")
            logo_url = st.text_input("URL del Logo", value="https://via.placeholder.com/150x150.png?text=LOGO", key="config_logo_url")
            
            st.markdown("### Opciones de Certificaciones")
            
            titulo_certificacion = st.text_input("Título de Certificaciones", value="CERTIFICACIÓN LABORAL", key="config_titulo_cert")
            nombre_firmante = st.text_input("Nombre del Firmante", value="Jefe de Talento Humano", key="config_firmante")
            
            st.markdown("### Configuración de Correo Electrónico")
            
            servidor_correo = st.text_input("Servidor SMTP", value="smtp.ejemplo.com", key="config_smtp_server")
            puerto_correo = st.number_input("Puerto SMTP", value=587, key="config_smtp_port")
            usuario_correo = st.text_input("Usuario SMTP", value="notificaciones@ejemplo.com", key="config_smtp_user")
            password_correo = st.text_input("Contraseña SMTP", type="password", key="config_smtp_password")
            
            guardar_config = st.form_submit_button("Guardar Configuración", use_container_width=True)
            
            if guardar_config:
                # En un sistema real, aquí se guardarían las configuraciones en la base de datos
                st.success("Configuración guardada correctamente")

# Página de gestión de usuarios
def usuarios_page():
    st.markdown('<h1 class="main-header">Gestión de Usuarios</h1>', unsafe_allow_html=True)
    
    # Verificar si el usuario tiene permisos de administrador
    if st.session_state.user['rol'] != 'admin':
        st.error("No tiene permisos para acceder a esta sección")
        return
    
    # Crear tabs para diferentes secciones
    tab1, tab2 = st.tabs(["Listar Usuarios", "Nuevo Usuario"])
    
    with tab1:
        st.markdown('<h3 class="section-header">Usuarios del Sistema</h3>', unsafe_allow_html=True)
        
        # Conectar a la base de datos
        conn = get_db_connection()
        usuarios = conn.execute("SELECT * FROM usuarios ORDER BY nombre_completo").fetchall()
        conn.close()
        
        if usuarios:
            # Convertir a dataframe para mostrar
            df_usuarios = pd.DataFrame([{
                'ID': u['id'],
                'Usuario': u['username'],
                'Nombre Completo': u['nombre_completo'],
                'Rol': u['rol'],
                'Estado': u['estado'],
                'Último Acceso': u['ultimo_acceso'] if u['ultimo_acceso'] else "Nunca"
            } for u in usuarios])
            
            st.dataframe(df_usuarios, use_container_width=True)
            
            # Seleccionar usuario para editar
            usuario_id = st.selectbox("Seleccionar usuario para editar", 
                                  [u['id'] for u in usuarios],
                                  format_func=lambda x: next((u['nombre_completo'] for u in usuarios if u['id'] == x), ''))
            
            if usuario_id:
                usuario_seleccionado = next((u for u in usuarios if u['id'] == usuario_id), None)
                
                if usuario_seleccionado:
                    with st.form("editar_usuario_form"):
                        st.text_input("Usuario", usuario_seleccionado['username'], key="edit_user_username")
                        st.text_input("Nombre Completo", usuario_seleccionado['nombre_completo'], key="edit_user_nombre")
                        st.selectbox("Rol", ["admin", "gestor", "consulta"], 
                                   index=["admin", "gestor", "consulta"].index(usuario_seleccionado['rol']) if usuario_seleccionado['rol'] in ["admin", "gestor", "consulta"] else 0,
                                   key="edit_user_rol")
                        st.selectbox("Estado", ["Activo", "Inactivo"], 
                                   index=["Activo", "Inactivo"].index(usuario_seleccionado['estado']) if usuario_seleccionado['estado'] in ["Activo", "Inactivo"] else 0,
                                   key="edit_user_estado")
                        
                        cambiar_password = st.checkbox("Cambiar Contraseña", key="edit_user_cambiar_password")
                        
                        if cambiar_password:
                            st.text_input("Nueva Contraseña", type="password", key="edit_user_password")
                            st.text_input("Confirmar Contraseña", type="password", key="edit_user_password_confirm")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            submit_edit = st.form_submit_button("Guardar Cambios", use_container_width=True)
                        
                        with col2:
                            delete_btn = st.form_submit_button("Eliminar Usuario", use_container_width=True)
                        
                        if submit_edit:
                            # Validar campos
                            if not st.session_state.edit_user_username or not st.session_state.edit_user_nombre:
                                st.error("Usuario y nombre son campos requeridos")
                            elif cambiar_password and st.session_state.edit_user_password != st.session_state.edit_user_password_confirm:
                                st.error("Las contraseñas no coinciden")
                            else:
                                # Conectar a la base de datos
                                conn = get_db_connection()
                                
                                try:
                                    if cambiar_password:
                                        conn.execute('''
                                            UPDATE usuarios 
                                            SET username = ?, nombre_completo = ?, rol = ?, estado = ?, password = ? 
                                            WHERE id = ?
                                        ''', (
                                            st.session_state.edit_user_username,
                                            st.session_state.edit_user_nombre,
                                            st.session_state.edit_user_rol,
                                            st.session_state.edit_user_estado,
                                            st.session_state.edit_user_password,
                                            usuario_id
                                        ))
                                    else:
                                        conn.execute('''
                                            UPDATE usuarios 
                                            SET username = ?, nombre_completo = ?, rol = ?, estado = ? 
                                            WHERE id = ?
                                        ''', (
                                            st.session_state.edit_user_username,
                                            st.session_state.edit_user_nombre,
                                            st.session_state.edit_user_rol,
                                            st.session_state.edit_user_estado,
                                            usuario_id
                                        ))
                                    
                                    conn.commit()
                                    conn.close()
                                    
                                    st.success("Usuario actualizado correctamente")
                                    st.experimental_rerun()
                                except sqlite3.IntegrityError as e:
                                    conn.close()
                                    if "UNIQUE constraint failed: usuarios.username" in str(e):
                                        st.error("Ya existe otro usuario con ese nombre de usuario")
                                    else:
                                        st.error(str(e))
                        
                        if delete_btn:
                            # Verificar si es el último usuario administrador
                            conn = get_db_connection()
                            admins_count = conn.execute(
                                "SELECT COUNT(*) FROM usuarios WHERE rol = 'admin' AND estado = 'Activo'"
                            ).fetchone()[0]
                            
                            if admins_count <= 1 and usuario_seleccionado['rol'] == 'admin' and usuario_seleccionado['estado'] == 'Activo':
                                conn.close()
                                st.error("No se puede eliminar el último usuario administrador activo")
                            else:
                                conn.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
                                conn.commit()
                                conn.close()
                                
                                st.success("Usuario eliminado correctamente")
                                st.experimental_rerun()
        else:
            st.info("No hay usuarios registrados")
    
    with tab2:
        st.markdown('<h3 class="section-header">Crear Nuevo Usuario</h3>', unsafe_allow_html=True)
        
        with st.form("nuevo_usuario_form"):
            st.text_input("Usuario", key="nuevo_username")
            st.text_input("Contraseña", type="password", key="nuevo_password")
            st.text_input("Confirmar Contraseña", type="password", key="nuevo_password_confirm")
            st.text_input("Nombre Completo", key="nuevo_nombre_completo")
            st.selectbox("Rol", ["admin", "gestor", "consulta"], key="nuevo_rol")
            
            submit = st.form_submit_button("Crear Usuario", use_container_width=True)
            
            if submit:
                # Validar campos
                if not st.session_state.nuevo_username or not st.session_state.nuevo_password or not st.session_state.nuevo_nombre_completo:
                    st.error("Todos los campos son requeridos")
                elif st.session_state.nuevo_password != st.session_state.nuevo_password_confirm:
                    st.error("Las contraseñas no coinciden")
                else:
                    # Conectar a la base de datos
                    conn = get_db_connection()
                    
                    try:
                        conn.execute('''
                            INSERT INTO usuarios (username, password, nombre_completo, rol, estado)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            st.session_state.nuevo_username,
                            st.session_state.nuevo_password,
                            st.session_state.nuevo_nombre_completo,
                            st.session_state.nuevo_rol,
                            'Activo'
                        ))
                        
                        conn.commit()
                        conn.close()
                        
                        st.success("Usuario creado correctamente")
                        st.experimental_rerun()
                    except sqlite3.IntegrityError as e:
                        conn.close()
                        if "UNIQUE constraint failed: usuarios.username" in str(e):
                            st.error("Ya existe un usuario con ese nombre de usuario")
                        else:
                            st.error(str(e))

# Página de ayuda
def ayuda_page():
    st.markdown('<h1 class="main-header">Ayuda y Soporte</h1>', unsafe_allow_html=True)
    
    # Crear tabs para diferentes secciones de ayuda
    tab1, tab2, tab3 = st.tabs(["Guía de Uso", "Tutoriales", "Soporte"])
    
    with tab1:
        st.markdown('<h3 class="section-header">Guía de Uso del Sistema</h3>', unsafe_allow_html=True)
        
        st.markdown("""
        ### Bienvenido al Sistema de Gestión de Recursos Humanos
        
        Este sistema le permite administrar la información relacionada con los cargos, servidores públicos, vinculaciones y traslados de su entidad.
        
        ### Funcionalidades Principales
        
        1. **Gestión de Cargos**: Crear, modificar y eliminar cargos. Cada cargo tiene información específica como su nomenclatura, nivel, naturaleza, asignación básica, entre otros.
        
        2. **Gestión de Servidores**: Administrar la información de los servidores públicos, incluyendo sus datos personales y laborales.
        
        3. **Vinculaciones y Traslados**: Registrar las vinculaciones de servidores a cargos, así como los traslados entre diferentes cargos.
        
        4. **Certificaciones**: Generar certificaciones laborales e historiales de cargos para los servidores.
        
        5. **Reportes y Estadísticas**: Obtener informes sobre cargos vacantes, distribución de personal, histórico de vinculaciones y estadísticas generales.
        
        ### Navegación
        
        El menú de navegación se encuentra en la barra lateral izquierda. Desde allí puede acceder a todas las funcionalidades del sistema.
        
        ### Roles de Usuario
        
        El sistema cuenta con tres roles de usuario:
        
        - **Administrador**: Tiene acceso completo a todas las funcionalidades del sistema, incluyendo la gestión de usuarios y configuración.
        - **Gestor**: Puede administrar cargos, servidores, vinculaciones y traslados, así como generar certificaciones y reportes.
        - **Consulta**: Solo puede consultar información, sin capacidad de crear, modificar o eliminar registros.
        """)
    
    with tab2:
        st.markdown('<h3 class="section-header">Tutoriales en Video</h3>', unsafe_allow_html=True)
        
        st.markdown("""
        ### Videos Tutoriales Disponibles
        
        A continuación, encontrará enlaces a videos tutoriales que le ayudarán a familiarizarse con el uso del sistema:
        
        1. **Introducción al Sistema**: Vista general de las funcionalidades y navegación.
        
        2. **Gestión de Cargos**: Cómo crear, modificar y gestionar los cargos en el sistema.
        
        3. **Gestión de Servidores**: Registro y administración de servidores públicos.
        
        4. **Vinculaciones y Traslados**: Proceso para registrar vinculaciones y realizar traslados.
        
        5. **Generación de Certificaciones**: Cómo generar diferentes tipos de certificaciones.
        
        6. **Reportes y Estadísticas**: Uso de las herramientas de reportes y análisis.
        
        7. **Configuración del Sistema**: Opciones de configuración para administradores.
        
        **Nota**: Los videos tutoriales no están disponibles en este prototipo. En un entorno de producción, aquí se incluirían enlaces a videos alojados en un servidor de la entidad o en plataformas como YouTube.
        """)
    
    with tab3:
        st.markdown('<h3 class="section-header">Soporte Técnico</h3>', unsafe_allow_html=True)
        
        st.markdown("""
        ### Opciones de Soporte
        
        Si necesita ayuda con el sistema, tiene las siguientes opciones:
        
        ### 1. FAQ (Preguntas Frecuentes)
        
        **¿Cómo restablezco mi contraseña?**  
        Si olvidó su contraseña, contacte al administrador del sistema para que la restablezca.
        
        **¿Puedo eliminar un cargo que tiene vinculaciones?**  
        No, primero debe finalizar o trasladar todas las vinculaciones asociadas a ese cargo.
        
        **¿Cómo genero una certificación laboral?**  
        Vaya a la sección "Certificaciones", seleccione el servidor y el periodo para el cual desea generar la certificación.
        
        **¿Cómo identifico los cargos vacantes?**  
        Puede encontrar los cargos vacantes en el Dashboard o en la sección de Reportes > Cargos Vacantes.
        
        ### 2. Contacto de Soporte
        
        Si no encuentra respuesta a su pregunta, puede contactar al equipo de soporte:
        
        **Email de soporte**: soporte.rrhh@ejemplo.com  
        **Teléfono**: (601) 123-4567  
        **Horario de atención**: Lunes a Viernes, 8:00 AM - 5:00 PM
        
        ### 3. Reportar Problemas
        
        Si encuentra algún error o problema técnico, por favor repórtelo utilizando el siguiente formulario:
        """)
        
        with st.form("reporte_problema_form"):
            st.text_input("Nombre", key="soporte_nombre")
            st.text_input("Email", key="soporte_email")
            st.selectbox("Tipo de Problema", 
                       ["Error Técnico", "Consulta de Uso", "Sugerencia de Mejora", "Otro"],
                       key="soporte_tipo_problema")
            st.text_area("Descripción del Problema", key="soporte_descripcion")
            st.file_uploader("Adjuntar Captura de Pantalla (opcional)", type=['png', 'jpg', 'jpeg'], key="soporte_captura")
            
            submit = st.form_submit_button("Enviar Reporte", use_container_width=True)
            
            if submit:
                # En un sistema real, aquí se enviaría el reporte por email o se guardaría en una base de datos
                st.success("Reporte enviado correctamente. El equipo de soporte se pondrá en contacto con usted pronto.")

# Función para obtener histórico de un cargo específico
def get_historico_por_cargo(cargo_id, fecha_inicio=None, fecha_fin=None):
    conn = get_db_connection()
    
    # Construir la consulta base
    query = '''
        SELECT v.*, s.nombres, s.apellidos, s.documento_identidad, s.tipo_documento,
               c.nombre_cargo, c.nomenclatura, c.nivel, c.dependencia
        FROM vinculaciones v
        JOIN servidores s ON v.servidor_id = s.id
        JOIN cargos c ON v.cargo_id = c.id
        WHERE v.cargo_id = ?
    '''
    
    params = [cargo_id]
    
    # Aplicar filtros de fecha si se proporcionan
    if fecha_inicio and fecha_fin:
        query += ' AND ((v.fecha_inicio BETWEEN ? AND ?) OR (v.fecha_fin BETWEEN ? AND ?) OR (v.fecha_inicio <= ? AND (v.fecha_fin >= ? OR v.fecha_fin IS NULL)))'
        params.extend([
            fecha_inicio, fecha_fin,
            fecha_inicio, fecha_fin,
            fecha_fin, fecha_inicio
        ])
    
    # Ejecutar la consulta
    historial = conn.execute(query, params).fetchall()
    
    # Obtener el nombre del cargo
    nombre_cargo = conn.execute('SELECT nombre_cargo FROM cargos WHERE id = ?', [cargo_id]).fetchone()['nombre_cargo']
    
    conn.close()
    
    return historial, nombre_cargo

# Calcular estadísticas del historial de un cargo
def calcular_estadisticas_cargo(historial):
    total_ocupantes = len(historial)
    
    # Calcular duración promedio (excluyendo vinculaciones actuales)
    duraciones = []
    for vinc in historial:
        if vinc['fecha_fin']:  # Solo para vinculaciones finalizadas
            fecha_inicio = datetime.strptime(vinc['fecha_inicio'], '%Y-%m-%d')
            fecha_fin = datetime.strptime(vinc['fecha_fin'], '%Y-%m-%d')
            duracion_dias = (fecha_fin - fecha_inicio).days
            duraciones.append(duracion_dias)
    
    duracion_promedio = sum(duraciones) / len(duraciones) if duraciones else 0
    
    # Actual ocupante
    actual_ocupante = None
    for vinc in historial:
        if not vinc['fecha_fin']:  # Vinculación sin fecha de fin (actual)
            actual_ocupante = {
                'nombre': f"{vinc['nombres']} {vinc['apellidos']}",
                'fecha_inicio': vinc['fecha_inicio']
            }
            break
    
    return {
        'total_ocupantes': total_ocupantes,
        'duracion_promedio_dias': duracion_promedio,
        'actual_ocupante': actual_ocupante
    }

# Función para mostrar la página de histórico por cargo en la interfaz
def historico_por_cargo_page():
    st.markdown('<h1 class="main-header">Histórico por Cargo</h1>', unsafe_allow_html=True)
    
    # Obtener todos los cargos
    cargos = get_all_cargos()
    
    # Crear selector de cargo
    cargo_options = [(c['id'], f"{c['nombre_cargo']} - {c['nomenclatura']} ({c['dependencia']})") for c in cargos]
    
    # Ordenar alfabéticamente por nombre del cargo
    cargo_options.sort(key=lambda x: x[1])
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        cargo_id = st.selectbox(
            "Seleccionar Cargo",
            options=[opt[0] for opt in cargo_options],
            format_func=lambda x: next((opt[1] for opt in cargo_options if opt[0] == x), ""),
            key="historico_cargo_selector"
        )
    
    # Filtros de fecha opcionales
    with col2:
        usar_filtro_fecha = st.checkbox("Filtrar por período", value=False, key="usar_filtro_fecha_cargo")
    
    if usar_filtro_fecha:
        col1, col2 = st.columns(2)
        with col1:
            fecha_inicio = st.date_input("Fecha de Inicio", value=datetime(datetime.now().year-5, 1, 1), key="hist_cargo_fecha_inicio")
        with col2:
            fecha_fin = st.date_input("Fecha de Fin", key="hist_cargo_fecha_fin")
        
        fecha_inicio_str = fecha_inicio.strftime('%Y-%m-%d')
        fecha_fin_str = fecha_fin.strftime('%Y-%m-%d')
    else:
        fecha_inicio_str = None
        fecha_fin_str = None
    
    if cargo_id:
        # Generar el reporte
        if st.button("Generar Reporte", key="btn_generar_hist_cargo", use_container_width=True):
            historial, nombre_cargo = get_historico_por_cargo(cargo_id, fecha_inicio_str, fecha_fin_str)
            
            if historial:
                # Título con el nombre del cargo
                st.markdown(f'<h2 class="section-header">Historial del cargo: {nombre_cargo}</h2>', unsafe_allow_html=True)
                
                # Estadísticas del cargo
                estadisticas = calcular_estadisticas_cargo(historial)
                
                # Mostrar información en tarjetas
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(label="Total de Ocupantes", value=estadisticas['total_ocupantes'])
                
                with col2:
                    if estadisticas['duracion_promedio_dias'] > 0:
                        duracion_años = estadisticas['duracion_promedio_dias'] / 365
                        if duracion_años < 1:
                            duracion_meses = estadisticas['duracion_promedio_dias'] / 30
                            st.metric(label="Duración Promedio", value=f"{duracion_meses:.1f} meses")
                        else:
                            st.metric(label="Duración Promedio", value=f"{duracion_años:.1f} años")
                    else:
                        st.metric(label="Duración Promedio", value="N/A")
                
                with col3:
                    if estadisticas['actual_ocupante']:
                        st.metric(
                            label="Ocupante Actual", 
                            value=estadisticas['actual_ocupante']['nombre'],
                            delta=f"Desde {estadisticas['actual_ocupante']['fecha_inicio']}"
                        )
                    else:
                        st.metric(label="Ocupante Actual", value="Vacante")
                
                # Tabla con el historial completo
                st.markdown("### Lista de servidores que han ocupado el cargo")
                
                # Convertir a dataframe para mostrar
                df_historial = pd.DataFrame([{
                    'Servidor': f"{h['nombres']} {h['apellidos']}",
                    'Documento': h['documento_identidad'],
                    'Tipo Documento': h['tipo_documento'],
                    'Fecha Inicio': h['fecha_inicio'],
                    'Fecha Fin': h['fecha_fin'] if h['fecha_fin'] else "Actual",
                    'Tipo Vinculación': h['tipo_vinculacion'],
                    'Resolución': h['resolucion_vinculacion'],
                    'Acta Posesión': h['acta_posesion']
                } for h in historial])
                
                # Ordenar por fecha de inicio (más reciente primero)
                df_historial = df_historial.sort_values(by='Fecha Inicio', ascending=False)
                
                st.dataframe(df_historial, use_container_width=True)
                
                # Opción para exportar
                if st.button("Exportar Histórico del Cargo", use_container_width=True):
                    export_data = [dict(h) for h in historial]
                    excel_href = generate_excel(export_data, f"historico_cargo_{nombre_cargo}")
                    st.markdown(excel_href, unsafe_allow_html=True)
            else:
                st.info(f"No se encontraron registros de ocupación para este cargo{' en el período seleccionado' if usar_filtro_fecha else ''}.")


# Función principal para manejar la navegación
def main():
    # Mostrar barra lateral si el usuario está autenticado
    if st.session_state.user:
        sidebar_menu()
    
    # Mostrar la página correspondiente según el estado de la sesión
    if st.session_state.page == 'login':
        login_page()
    elif st.session_state.page == 'dashboard':
        dashboard_page()
    elif st.session_state.page == 'cargos':
        cargos_page()
    elif st.session_state.page == 'servidores':
        servidores_page()
    elif st.session_state.page == 'vinculaciones':
        vinculaciones_page()
    elif st.session_state.page == 'traslados':
        traslados_page()
    elif st.session_state.page == 'certificaciones':
        certificaciones_page()
    elif st.session_state.page == 'reportes':
        reportes_page()
    elif st.session_state.page == 'configuracion':
        configuracion_page()
    elif st.session_state.page == 'usuarios':
        usuarios_page()
    elif st.session_state.page == 'ayuda':
        ayuda_page()
    elif st.session_state.page == 'historico_cargo':
        historico_por_cargo_page()
    else:
        st.error("Página no encontrada")

# Ejecutar la aplicación
if __name__ == "__main__":
    main()