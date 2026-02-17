import os
from dotenv import load_dotenv
from google import genai

# 1. Cargar las variables del archivo .env
load_dotenv()

# 2. Obtener la API Key desde el entorno
api_key = os.environ.get("GEMINI_API_KEY")


client = genai.Client(api_key=api_key)


#Se Define el esquema de respuesta
schema_fiscal = {
    "type": "OBJECT",
    "properties": {
        "nombre_cliente": {"type": "STRING", "nullable": True},
        "monto": {"type": "NUMBER", "nullable": True},
        "fecha": {"type": "STRING", "nullable": True},
        "tipo_solicitud": {
            "type": "STRING", 
            "enum": ["Venta", "Queja", "Factura"] # Restringimos las opciones
        }
    },
    "required": ["nombre_cliente", "monto", "fecha", "tipo_solicitud"]
}



"""
response = client.models.generate_content(
    model="gemini-3-flash-preview",
    contents="Explain how AI works in a few words",
)

print(response.text)"""