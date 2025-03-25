import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import timedelta, date

st.set_page_config(page_title="Análisis de Uso de Aplicación", layout="wide")

@st.cache_data
def cargar_datos(path):
    columnas = ['ID', 'Modulo', 'Accion', 'UsuarioID', 'Rol', 'Entidad', 'Timestamp']
    try:
        df = pd.read_csv(path, sep=";", header=None, names=columnas, encoding="utf-8")
        df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
        df = df.dropna(subset=['Timestamp'])
        df['UsuarioID'] = df['UsuarioID'].astype(str).str.upper()
        df[['TipoDoc', 'NumeroDoc']] = df['UsuarioID'].str.extract(r'([A-Z]+)\|(\d+)', expand=True)
        df['Fecha'] = df['Timestamp'].dt.date
        df['Hora'] = df['Timestamp'].dt.hour
        return df
    except Exception as e:
        st.error(f"❌ Error cargando archivo: {e}")
        return pd.DataFrame()

archivo = r"C:\Users\edwin.paz\Desktop\marcadores de uso 2024-2025 - 14-03-25.csv"
df = cargar_datos(archivo)

if df.empty:
    st.error("🚫 El archivo está vacío o no contiene datos válidos.")
    st.stop()

st.sidebar.title("Filtros")

usuarios = st.sidebar.multiselect("Usuario(s)", sorted(df['NumeroDoc'].dropna().unique()))
entidades = st.sidebar.multiselect("Entidad(es)", sorted(df['Entidad'].dropna().unique()))
roles = st.sidebar.multiselect("Rol(es)", sorted(df['Rol'].dropna().unique()))
acciones = st.sidebar.multiselect("Acción(es)", sorted(df['Accion'].dropna().unique()))

min_fecha = df['Fecha'].min()
max_fecha = df['Fecha'].max()

if pd.isnull(min_fecha) or pd.isnull(max_fecha):
    hoy = date.today()
    fecha_inicio = st.sidebar.date_input("Desde", hoy)
    fecha_fin = st.sidebar.date_input("Hasta", hoy)
    st.warning("⚠️ No se detectaron fechas válidas.")
else:
    fecha_inicio = st.sidebar.date_input("Desde", min_fecha)
    fecha_fin = st.sidebar.date_input("Hasta", max_fecha)

df_filtrado = df[
    (df['Fecha'] >= fecha_inicio) & 
    (df['Fecha'] <= fecha_fin)
]

if usuarios:
    df_filtrado = df_filtrado[df_filtrado['NumeroDoc'].isin(usuarios)]
if entidades:
    df_filtrado = df_filtrado[df_filtrado['Entidad'].isin(entidades)]
if roles:
    df_filtrado = df_filtrado[df_filtrado['Rol'].isin(roles)]
if acciones:
    df_filtrado = df_filtrado[df_filtrado['Accion'].isin(acciones)]

if df_filtrado.empty:
    st.warning("⚠️ No hay datos que coincidan con los filtros seleccionados.")
    st.stop()

st.title("📊 Análisis de Uso de la Aplicación")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Registros", len(df_filtrado))
col2.metric("Usuarios únicos", df_filtrado['NumeroDoc'].nunique())
col3.metric("Entidades únicas", df_filtrado['Entidad'].nunique())
col4.metric("Acciones únicas", df_filtrado['Accion'].nunique())

actividad_dia = df_filtrado.groupby('Fecha').size()
st.subheader("📅 Actividad por Día")
fig1, ax1 = plt.subplots(figsize=(10, 3))
actividad_dia.plot(ax=ax1)
ax1.set_xlabel("Fecha")
ax1.set_ylabel("Eventos")
st.pyplot(fig1)

actividad_hora = df_filtrado.groupby('Hora').size()
st.subheader("🕓 Actividad por Hora del Día")
fig2, ax2 = plt.subplots(figsize=(8, 3))
actividad_hora.plot(kind='bar', ax=ax2)
ax2.set_xlabel("Hora")
ax2.set_ylabel("Eventos")
st.pyplot(fig2)

st.subheader("🔥 Heatmap Día x Hora")
pivot = df_filtrado.pivot_table(index='Hora', columns='Fecha', values='ID', aggfunc='count')
fig3, ax3 = plt.subplots(figsize=(14, 5))
sns.heatmap(pivot, cmap="YlGnBu", ax=ax3)
st.pyplot(fig3)

st.subheader("👤 Top 10 Usuarios Activos")
top_usuarios = df_filtrado['NumeroDoc'].value_counts().head(10)
st.bar_chart(top_usuarios)

st.subheader("🏢 Top 10 Entidades Activas")
top_entidades = df_filtrado['Entidad'].value_counts().head(10)
st.bar_chart(top_entidades)

st.subheader("⚙️ Acciones Más Usadas")
top_acciones = df_filtrado['Accion'].value_counts()
st.bar_chart(top_acciones)

st.subheader("🕳️ Estimación de Huecos de Actividad")
df_sorted = df_filtrado.sort_values('Timestamp')
df_sorted['Delta'] = df_sorted['Timestamp'].diff()
huecos = df_sorted[df_sorted['Delta'] > timedelta(minutes=15)]

st.write(f"Se detectaron **{len(huecos)}** posibles períodos de inactividad (>15 min).")
st.dataframe(huecos[['Timestamp', 'Delta']].head(10))

st.subheader("🧠 Comentarios Automáticos")
comentarios = []

if len(huecos) > 0:
    comentarios.append(f"⚠️ Hay {len(huecos)} posibles huecos de actividad.")
else:
    comentarios.append("✅ No se detectaron huecos significativos en el uso.")

if not df_filtrado.empty:
    dia_max = actividad_dia.idxmax()
    comentarios.append(f"📈 El día con más actividad fue **{dia_max}** con {actividad_dia.max()} eventos.")
    hora_max = actividad_hora.idxmax()
    comentarios.append(f"⏰ La hora más activa es alrededor de las **{hora_max}:00**.")
    usuario_top = top_usuarios.idxmax()
    comentarios.append(f"👤 El usuario más activo fue **{usuario_top}** con {top_usuarios.max()} acciones.")
    entidad_top = top_entidades.idxmax()
    comentarios.append(f"🏢 La entidad con más interacción fue **{entidad_top}**.")

for comentario in comentarios:
    st.markdown(comentario)
