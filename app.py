import os
import json
import pandas as pd
from dotenv import load_dotenv
from google import genai
from google.genai import types
from docx import Document

# --- 1. CONFIGURACIÓN DEL ENTORNO Y API ---

# Cargar variables de entorno desde .env
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    raise ValueError("❌ Error: No se encontró la variable GEMINI_API_KEY en el archivo .env")

# Inicializar cliente (SDK Nuevo: google-genai)
client = genai.Client(api_key=api_key)

# Definir la estructura estricta de salida (JSON Schema)
# Esto garantiza que la IA no alucine formatos.
schema_fiscal = {
    "type": "OBJECT",
    "properties": {
        "nombre_cliente": {"type": "STRING", "nullable": True},
        "monto": {"type": "NUMBER", "nullable": True},
        "fecha": {"type": "STRING", "nullable": True},
        "tipo_solicitud": {
            "type": "STRING",
            "enum": ["Venta", "Queja", "Factura"]
        }
    },
    "required": ["nombre_cliente", "monto", "fecha", "tipo_solicitud"]
}

# --- 2. CONFIGURACIÓN DE RUTAS (ROBUSTEZ UBUNTU) ---

# Obtiene la ruta absoluta de donde está ESTE script.
# Vital para que funcione con Cron o desde cualquier terminal en Linux.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "dummy")

print(f"📂 Directorio de trabajo: {BASE_DIR}")
print(f"📂 Buscando archivos en: {DATA_DIR}\n")

# --- 3. FUNCIONES DE LECTURA (ETL) ---

def leer_txt(filepath):
    """Lee un archivo de texto plano línea por línea."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f.readlines() if len(line.strip()) > 10]
    except Exception as e:
        print(f"⚠️ Error leyendo TXT: {e}")
        return []

def leer_docx(filepath):
    """Lee los párrafos de un archivo Word."""
    try:
        doc = Document(filepath)
        return [p.text.strip() for p in doc.paragraphs if len(p.text.strip()) > 10]
    except Exception as e:
        print(f"⚠️ Error leyendo DOCX: {e}")
        return []

def leer_csv(filepath, columna):
    """Lee una columna específica de un CSV."""
    try:
        df = pd.read_csv(filepath)
        if columna in df.columns:
            return df[columna].dropna().tolist()
        else:
            print(f"⚠️ Columna '{columna}' no encontrada en CSV.")
            return []
    except Exception as e:
        print(f"⚠️ Error leyendo CSV: {e}")
        return []

# --- 4. FUNCIÓN DE EXTRACCIÓN CON IA ---

def analizar_texto(texto):
    prompt = f"""
    Analiza este mensaje de cliente. Extrae: Cliente, Monto, Fecha y Tipo (Venta/Queja/Factura).
    Si el dato no existe, usa null. Si la fecha es relativa (ej: 'ayer'), calcúlala asumiendo hoy es 2026-02-17.
    
    MENSAJE: "{texto}"
    """
    
    try:
        response = client.models.generate_content(
            model="gemini-3-flash-preview", 
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema_fiscal,
                temperature=0.1 # Baja temperatura para mayor precisión
            )
        )
        # Parsear la respuesta JSON
        return json.loads(response.text)
    except Exception as e:
        print(f"❌ Error en la API con el texto: '{texto[:20]}...' -> {e}")
        return None

# --- 5. ORQUESTADOR PRINCIPAL ---

def main():
    todos_los_mensajes = []
    
    # --- A. INGESTA DE DATOS ---
    print("--- INICIANDO LECTURA DE ARCHIVOS ---")
    
    # 1. TXT
    ruta_txt = os.path.join(DATA_DIR, "dummytxt.txt")
    if os.path.exists(ruta_txt):
        datos = leer_txt(ruta_txt)
        todos_los_mensajes.extend(datos)
        print(f"✅ TXT cargado ({len(datos)} registros)")
    
    # 2. DOCX
    ruta_docx = os.path.join(DATA_DIR, "dummyword.docx")
    if os.path.exists(ruta_docx):
        datos = leer_docx(ruta_docx)
        todos_los_mensajes.extend(datos)
        print(f"✅ DOCX cargado ({len(datos)} registros)")

    # 3. CSV
    ruta_csv = os.path.join(DATA_DIR, "dummycsv.csv")
    if os.path.exists(ruta_csv):
        # Asegúrate que tu CSV tenga la columna 'texto_mensaje' o cámbialo aquí
        datos = leer_csv(ruta_csv, "texto_mensaje") 
        todos_los_mensajes.extend(datos)
        print(f"✅ CSV cargado ({len(datos)} registros)")

    total = len(todos_los_mensajes)
    print(f"\nTOTAL A PROCESAR: {total} registros")
    
    if total == 0:
        print("❌ No hay datos para procesar. Revisa la carpeta 'datos_entrada'.")
        return

    # --- B. PROCESAMIENTO CON IA ---
    print("\n--- INICIANDO ANÁLISIS CON GEMINI ---")
    resultados = []
    
    for i, mensaje in enumerate(todos_los_mensajes):
        # Barra de progreso simple
        if i % 5 == 0: print(f"Procesando {i+1}/{total}...")
        
        info_extraida = analizar_texto(mensaje)
        
        if info_extraida:
            # Agregamos el mensaje original para tener contexto en el Excel final
            info_extraida["mensaje_original"] = mensaje
            resultados.append(info_extraida)

    # --- C. GUARDADO DE RESULTADOS ---
    print("\n--- GUARDANDO REPORTE ---")
    
    if resultados:
        df_final = pd.DataFrame(resultados)
        
        # Reordenar columnas para mejor lectura
        cols = ["nombre_cliente", "monto", "fecha", "tipo_solicitud", "mensaje_original"]
        # Aseguramos que existan todas las columnas aunque vengan vacías
        for col in cols:
            if col not in df_final.columns:
                df_final[col] = None
                
        df_final = df_final[cols]
        
        nombre_reporte = "Reporte_Final_Clientes.xlsx"
        df_final.to_excel(nombre_reporte, index=False)
        
        print(f"🎉 ¡ÉXITO! Se generó el archivo '{nombre_reporte}' con {len(df_final)} registros procesados.")
        print(df_final.head())
    else:
        print("⚠️ No se generaron resultados válidos.")

if __name__ == "__main__":
    main()
"""
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Explain how AI works in a few words",
)

print(response.text)"""