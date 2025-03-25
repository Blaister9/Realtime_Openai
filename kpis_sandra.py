import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from datetime import timedelta

# -------------------------------
# 1. Cargar datos
# -------------------------------
file_path = r"C:\Users\edwin.paz\Desktop\marcadores de uso 2024-2025 - 14-03-25.csv"

columnas = ['ID', 'Modulo', 'Accion', 'UsuarioID', 'Rol', 'Entidad', 'Timestamp']
df = pd.read_csv(file_path, sep="\t", header=None, names=columnas)

# -------------------------------
# 2. Limpieza básica
# -------------------------------
df['Timestamp'] = pd.to_datetime(df['Timestamp'], errors='coerce')
df.dropna(subset=['Timestamp'], inplace=True)
df[['TipoDoc', 'NumeroDoc']] = df['UsuarioID'].str.upper().str.split('|', expand=True)

# -------------------------------
# 3. KPIs generales
# -------------------------------
total_registros = len(df)
usuarios_unicos = df['NumeroDoc'].nunique()
entidades_unicas = df['Entidad'].nunique()
acciones_unicas = df['Accion'].nunique()

print(f"Total de registros: {total_registros}")
print(f"Usuarios únicos: {usuarios_unicos}")
print(f"Entidades únicas: {entidades_unicas}")
print(f"Acciones únicas: {acciones_unicas}")

# -------------------------------
# 4. Actividad por día y hora
# -------------------------------
df['Fecha'] = df['Timestamp'].dt.date
df['Hora'] = df['Timestamp'].dt.hour
actividad_dia = df.groupby('Fecha').size()
actividad_hora = df.groupby('Hora').size()

# -------------------------------
# 5. Usuarios más activos
# -------------------------------
top_usuarios = df['NumeroDoc'].value_counts().head(10)

# -------------------------------
# 6. Acciones más usadas
# -------------------------------
acciones = df['Accion'].value_counts()

# -------------------------------
# 7. Entidades más activas
# -------------------------------
top_entidades = df['Entidad'].value_counts().head(10)

# -------------------------------
# 8. Estimación de disponibilidad
# -------------------------------
df_sorted = df.sort_values('Timestamp')
df_sorted['Delta'] = df_sorted['Timestamp'].diff()
huecos = df_sorted[df_sorted['Delta'] > timedelta(minutes=15)]

print(f"\nPosibles huecos de actividad detectados (Delta > 15 minutos): {len(huecos)}")
print(huecos[['Timestamp', 'Delta']].head())

# -------------------------------
# 9. Visualizaciones
# -------------------------------

# Actividad por día
plt.figure(figsize=(12, 4))
actividad_dia.plot()
plt.title("Actividad por Día")
plt.xlabel("Fecha")
plt.ylabel("Número de eventos")
plt.grid()
plt.tight_layout()
plt.show()

# Actividad por hora
plt.figure(figsize=(8, 4))
actividad_hora.plot(kind='bar')
plt.title("Actividad por Hora del Día")
plt.xlabel("Hora")
plt.ylabel("Número de eventos")
plt.grid()
plt.tight_layout()
plt.show()

# Usuarios más activos
top_usuarios.plot(kind='barh', title="Top 10 Usuarios Más Activos")
plt.xlabel("Cantidad de clics")
plt.tight_layout()
plt.show()

# Entidades más activas
top_entidades.plot(kind='barh', title="Top 10 Entidades Más Activas", color='green')
plt.xlabel("Cantidad de clics")
plt.tight_layout()
plt.show()

# Acciones más comunes
acciones.plot(kind='bar', title="Distribución de Acciones")
plt.ylabel("Frecuencia")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# Heatmap de actividad
pivot = df.pivot_table(index=df['Hora'], columns=df['Fecha'], values='ID', aggfunc='count')
plt.figure(figsize=(16, 6))
sns.heatmap(pivot, cmap="YlGnBu", linewidths=0.5)
plt.title("Heatmap de Actividad por Hora y Día")
plt.tight_layout()
plt.show()

# -------------------------------
# 10. Comentarios automáticos
# -------------------------------
print("\n--- Comentarios Automáticos ---")

if len(huecos) > 0:
    print(f"⚠️ Se detectaron {len(huecos)} posibles períodos de inactividad (>15 min).")
else:
    print("✅ No se detectaron huecos significativos en la actividad.")

print(f"📈 El día con mayor actividad fue: {actividad_dia.idxmax()} ({actividad_dia.max()} eventos)")
print(f"🕓 La hora más activa del día es: {actividad_hora.idxmax()}h")
print(f"👤 Usuario más activo: {top_usuarios.index[0]} con {top_usuarios.iloc[0]} eventos")
print(f"🏢 Entidad más activa: {top_entidades.index[0]} con {top_entidades.iloc[0]} eventos")

