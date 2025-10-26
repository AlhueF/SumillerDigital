from pymongo import MongoClient
import datetime
import urllib.parse

# Función para intentar diferentes conexiones a MongoDB
def conectar_mongodb():
    """
    Intenta conectar a MongoDB usando diferentes configuraciones
    """
    conexiones = [
        ('local', 'mongodb://localhost:27017/'),
        ('atlas', 'mongodb+srv://test:test@cluster0.mongodb.net/test')  # Conexión de ejemplo
    ]
    
    for nombre, uri in conexiones:
        try:
            print(f"Intentando conexión a MongoDB ({nombre})...")
            client = MongoClient(uri, serverSelectionTimeoutMS=5000)
            # Verificar la conexión
            client.server_info()
            print(f"✅ Conexión exitosa a MongoDB ({nombre})")
            return client
        except Exception as e:
            print(f"❌ Error conectando a {nombre}: {e}")
    
    raise Exception("No se pudo conectar a ninguna instancia de MongoDB")

try:
    # Intentar conectar a MongoDB
    client = conectar_mongodb()
    db = client['menu_database']
    collection = db['platos']
    print("✅ Base de datos y colección configuradas")
except Exception as e:
    print(f"❌ Error fatal: {e}")
    print("\nPor favor, asegúrate de que MongoDB está instalado y ejecutándose:")
    print("1. Descarga MongoDB: https://www.mongodb.com/try/download/community")
    print("2. Instala seleccionando 'Complete' y 'Install as a Service'")
    print("3. Reinicia el notebook después de la instalación")

def guardar_plato_en_mongodb(plato_dict):
    """
    Guarda un plato en MongoDB con timestamp
    """
    # Añadir timestamp
    plato_dict['timestamp'] = datetime.datetime.now()
    
    try:
        # Insertar en MongoDB
        result = collection.insert_one(plato_dict)
        print(f"✅ Plato guardado con ID: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        print(f"❌ Error al guardar en MongoDB: {e}")
        return None

def obtener_platos_guardados():
    """
    Recupera todos los platos guardados
    """
    try:
        platos = list(collection.find())
        return platos
    except Exception as e:
        print(f"❌ Error al recuperar platos: {e}")
        return []