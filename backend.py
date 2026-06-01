# ============================================================
# SMART WAREHOUSE - Backend Python
# Lee el puerto serial del Arduino e inserta en MongoDB
# ============================================================

import serial
import pymongo
from datetime import datetime, timedelta

# ============================================================
# CONFIGURACIÓN
# ============================================================
PUERTO_SERIAL = "COM5"
BAUDRATE      = 9600
MONGO_URI     = "mongodb://localhost:27017"
NOMBRE_DB     = "smart_warehouse"

# ============================================================
# CONEXIÓN A MONGODB
# ============================================================
cliente   = pymongo.MongoClient(MONGO_URI)
db        = cliente[NOMBRE_DB]
col_logs  = db["sensor_logs"]
col_alert = db["alertas"]

print("✓ Conectado a MongoDB")

# ============================================================
# FUNCIÓN: parsear_linea
# ============================================================
def parsear_linea(linea):
    try:
        partes = linea.strip().split(",")

        datos = {}
        for parte in partes:
            clave, valor = parte.split(":")
            datos[clave.strip()] = valor.strip()

        documento = {
            "timestamp":     datetime.now(),
            "pir":           int(datos["PIR"]),
            "ldr":           int(datos["LDR"]),
            "distancia_cm":  float(datos["DIST"]),
            "stock_ok":      int(datos["STOCK"]) == 1,
            "led_amarillo":  int(datos["LED_AMAR"]) == 1,
            "led_rojo":      int(datos["LED_ROJO"]) == 1,
            "servo_grados":  int(datos["SERVO"]),
            "buzzer":        int(datos["BUZZ"]) == 1
        }

        return documento

    except Exception as e:
        print(f"  ✗ Línea ignorada (mal formato): {linea} | Error: {e}")
        return None

# ============================================================
# FUNCIÓN: registrar_alerta
# Con cooldown de 30 segundos para no duplicar alertas
# ============================================================
estado_anterior_stock = True
ultima_alerta_tiempo  = None

def registrar_alerta(documento):
    global estado_anterior_stock, ultima_alerta_tiempo

    stock_actual = documento["stock_ok"]
    ahora        = datetime.now()

    cooldown_ok = (
        ultima_alerta_tiempo is None or
        ahora - ultima_alerta_tiempo > timedelta(seconds=30)
    )

    if not stock_actual and estado_anterior_stock and cooldown_ok:
        alerta = {
            "timestamp":    documento["timestamp"],
            "tipo":         "QUIEBRE_STOCK",
            "distancia_cm": documento["distancia_cm"],
            "mensaje":      f"Estante vacío detectado. Distancia: {documento['distancia_cm']} cm."
        }
        col_alert.insert_one(alerta)
        ultima_alerta_tiempo = ahora
        print(f"  ⚠ ALERTA insertada: quiebre de stock a {documento['distancia_cm']} cm")

    estado_anterior_stock = stock_actual

# ============================================================
# BUCLE PRINCIPAL
# ============================================================
print(f"✓ Abriendo puerto {PUERTO_SERIAL} a {BAUDRATE} baudios...")

try:
    arduino = serial.Serial(PUERTO_SERIAL, BAUDRATE, timeout=2)
    print(f"✓ Puerto {PUERTO_SERIAL} abierto. Escuchando Arduino...\n")

    while True:
        linea_cruda  = arduino.readline()
        linea_texto  = linea_cruda.decode("utf-8", errors="ignore").strip()

        if not linea_texto or linea_texto == "SISTEMA_INICIADO":
            continue

        print(f"← Arduino: {linea_texto}")

        documento = parsear_linea(linea_texto)

        if documento:
            col_logs.insert_one(documento)
            print(f"  ✓ Insertado en sensor_logs")
            registrar_alerta(documento)

except serial.SerialException as e:
    print(f"\n✗ Error de puerto serial: {e}")
    print(f"  Verifica que el Arduino esté conectado en {PUERTO_SERIAL}")
    print(f"  y que el Serial Monitor del Arduino IDE esté CERRADO")

except KeyboardInterrupt:
    print("\n✓ Backend detenido por el usuario")
    arduino.close()
    cliente.close()
    print("✓ Conexiones cerradas correctamente")