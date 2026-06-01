import pymongo
from datetime import datetime, timedelta

cliente = pymongo.MongoClient("mongodb://localhost:27017")
db = cliente["smart_warehouse"]

# Borra documentos de sensor_logs con más de 24 horas de antigüedad
limite = datetime.now() - timedelta(hours=24)
resultado = db["sensor_logs"].delete_many({"timestamp": {"$lt": limite}})
print(f"✓ {resultado.deleted_count} documentos eliminados de sensor_logs")

cliente.close()