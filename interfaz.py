# ============================================================
# SMART WAREHOUSE - Interfaz Gráfica + Asistente LLM
# Panel de control en Tkinter con chat integrado (Claude)
# ============================================================

import tkinter as tk
from tkinter import ttk, scrolledtext
import pymongo
from datetime import datetime
import threading
import google.generativeai as genai

# ============================================================
# CONFIGURACIÓN
# ============================================================
MONGO_URI    = "mongodb://localhost:27017"
NOMBRE_DB    = "smart_warehouse"
API_KEY      = "AIzaSyAaC6vQjiM7mPqOngxI3rSCotY6dZpaad4"  # ← Pega tu clave aquí

# ============================================================
# CONEXIÓN A MONGODB
# ============================================================
cliente  = pymongo.MongoClient(MONGO_URI)
db       = cliente[NOMBRE_DB]
col_logs = db["sensor_logs"]
col_alert= db["alertas"]

# ============================================================
# CONEXIÓN AL LLM (Claude de Anthropic)
# ============================================================
genai.configure(api_key=API_KEY)
llm = genai.GenerativeModel("gemini-3-flash-preview")

# ============================================================
# FUNCIÓN: obtener_ultimo_estado
# Lee el documento más reciente de sensor_logs
# ============================================================
def obtener_ultimo_estado():
    doc = col_logs.find_one(sort=[("timestamp", pymongo.DESCENDING)])
    return doc

# ============================================================
# FUNCIÓN: obtener_resumen_para_llm
# Construye un texto con el historial reciente para darle
# contexto al LLM antes de responder
# ============================================================
def obtener_resumen_para_llm():
    # Tomamos los últimos 20 documentos de sensor_logs
    logs = list(col_logs.find(
        sort=[("timestamp", pymongo.DESCENDING)],
        limit=20
    ))

    # Tomamos las últimas 5 alertas
    alertas = list(col_alert.find(
        sort=[("timestamp", pymongo.DESCENDING)],
        limit=5
    ))

    # Construimos el texto de contexto
    resumen = "=== ESTADO ACTUAL DEL ALMACÉN ===\n"

    if logs:
        ultimo = logs[0]
        resumen += f"Última lectura: {ultimo['timestamp']}\n"
        resumen += f"  PIR (movimiento): {'Sí' if ultimo['pir'] else 'No'}\n"
        resumen += f"  LDR (luz): {ultimo['ldr']} (escala 0-1023)\n"
        resumen += f"  Distancia estante: {ultimo['distancia_cm']} cm\n"
        resumen += f"  Stock: {'OK' if ultimo['stock_ok'] else 'QUIEBRE'}\n"
        resumen += f"  LED amarillo: {'Encendido' if ultimo['led_amarillo'] else 'Apagado'}\n"
        resumen += f"  LED rojo: {'Encendido' if ultimo['led_rojo'] else 'Apagado'}\n"
        resumen += f"  Servo (barrera): {ultimo['servo_grados']}°\n"
        resumen += f"  Buzzer: {'Activo' if ultimo['buzzer'] else 'Silencio'}\n"

    resumen += f"\n=== ÚLTIMAS {len(alertas)} ALERTAS ===\n"
    if alertas:
        for a in alertas:
            resumen += f"  [{a['timestamp']}] {a['tipo']}: {a['mensaje']}\n"
    else:
        resumen += "  Sin alertas recientes.\n"

    resumen += f"\n=== HISTORIAL RECIENTE ({len(logs)} lecturas) ===\n"
    for log in logs[:5]:  # Mostramos solo los últimos 5 al LLM
        resumen += (
            f"  {log['timestamp']} | "
            f"PIR:{log['pir']} | "
            f"LDR:{log['ldr']} | "
            f"DIST:{log['distancia_cm']}cm | "
            f"STOCK:{'OK' if log['stock_ok'] else 'QUIEBRE'}\n"
        )

    return resumen

# ============================================================
# FUNCIÓN: consultar_llm
# Envía la pregunta del usuario + el contexto del almacén al LLM
# ============================================================
def consultar_llm(pregunta_usuario):
    contexto = obtener_resumen_para_llm()

    system_prompt = """Eres un asistente logístico virtual especializado en el 
monitoreo de un almacén inteligente (Smart Warehouse). Tienes acceso a datos 
en tiempo real de sensores IoT: sensor de movimiento PIR, fotorresistor LDR, 
sensor ultrasónico HC-SR04, servomotor y buzzer. 

Tu rol es interpretar estos datos y responder en español de forma clara, 
concisa y útil para el administrador del almacén. Puedes identificar patrones, 
alertas críticas, recomendar acciones y generar reportes operativos.

Cuando detectes quiebre de stock, barrera activada o anomalías, indícalo 
claramente con recomendaciones concretas."""

    mensaje_completo = f"{system_prompt}\n\n{contexto}\n\n=== PREGUNTA DEL OPERARIO ===\n{pregunta_usuario}"

    respuesta = llm.generate_content(mensaje_completo)
    return respuesta.text
# ============================================================
# CLASE PRINCIPAL: InterfazWarehouse
# Construye y gestiona toda la ventana de Tkinter
# ============================================================
class InterfazWarehouse:

    def __init__(self, root):
        self.root = root
        self.root.title("Smart Warehouse — Panel de Control")
        self.root.geometry("900x650")
        self.root.configure(bg="#1e1e2e")
        self.root.resizable(True, True)

        # Colores del tema oscuro
        self.COLOR_BG       = "#1e1e2e"
        self.COLOR_PANEL    = "#2a2a3e"
        self.COLOR_BORDE    = "#3a3a5e"
        self.COLOR_TEXTO    = "#cdd6f4"
        self.COLOR_MUTED    = "#6c7086"
        self.COLOR_VERDE    = "#a6e3a1"
        self.COLOR_ROJO     = "#f38ba8"
        self.COLOR_AMARILLO = "#f9e2af"
        self.COLOR_AZUL     = "#89b4fa"
        self.COLOR_ACENTO   = "#cba6f7"

        self._construir_ui()

        # Iniciamos la actualización automática cada 2 segundos
        self._actualizar_panel()

    # ----------------------------------------------------------
    # CONSTRUCCIÓN DE LA INTERFAZ
    # ----------------------------------------------------------
    def _construir_ui(self):

        # ── Título principal ──
        titulo = tk.Label(
            self.root,
            text="⬡  SMART WAREHOUSE — Panel de Control IoT",
            font=("Consolas", 14, "bold"),
            bg=self.COLOR_BG,
            fg=self.COLOR_ACENTO,
            pady=12
        )
        titulo.pack(fill="x")

        # ── Contenedor principal dividido en dos columnas ──
        contenedor = tk.Frame(self.root, bg=self.COLOR_BG)
        contenedor.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # Columna izquierda: panel de sensores
        self.col_izq = tk.Frame(contenedor, bg=self.COLOR_BG, width=380)
        self.col_izq.pack(side="left", fill="both", expand=False, padx=(0, 6))
        self.col_izq.pack_propagate(False)

        # Columna derecha: chat con LLM
        col_der = tk.Frame(contenedor, bg=self.COLOR_BG)
        col_der.pack(side="left", fill="both", expand=True, padx=(6, 0))

        self._construir_panel_sensores(self.col_izq)
        self._construir_panel_chat(col_der)

    def _construir_panel_sensores(self, parent):

        # ── Sección: Estado en tiempo real ──
        lbl_sec = tk.Label(
            parent, text="● SENSORES EN TIEMPO REAL",
            font=("Consolas", 10, "bold"),
            bg=self.COLOR_BG, fg=self.COLOR_MUTED, anchor="w", pady=4
        )
        lbl_sec.pack(fill="x")

        panel = tk.Frame(parent, bg=self.COLOR_PANEL,
                         highlightbackground=self.COLOR_BORDE,
                         highlightthickness=1)
        panel.pack(fill="x", pady=(0, 10))

        # Diccionario con las etiquetas de valor para actualizarlas después
        self.lbl_vals = {}

        sensores = [
            ("PIR — Movimiento",  "pir_texto",   "●"),
            ("LDR — Luminosidad", "ldr_texto",   "◈"),
            ("HC-SR04 — Distancia","dist_texto",  "◎"),
            ("Stock",             "stock_texto",  "▣"),
            ("LED Amarillo",      "led_am_texto", "◉"),
            ("LED Rojo",          "led_rj_texto", "◉"),
            ("Servo (barrera)",   "servo_texto",  "⊕"),
            ("Buzzer",            "buzz_texto",   "♪"),
        ]

        for nombre, clave, icono in sensores:
            fila = tk.Frame(panel, bg=self.COLOR_PANEL)
            fila.pack(fill="x", padx=12, pady=5)

            tk.Label(
                fila, text=f"{icono} {nombre}",
                font=("Consolas", 10),
                bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO,
                width=22, anchor="w"
            ).pack(side="left")

            val = tk.Label(
                fila, text="—",
                font=("Consolas", 10, "bold"),
                bg=self.COLOR_PANEL, fg=self.COLOR_MUTED,
                anchor="e"
            )
            val.pack(side="right", padx=8)
            self.lbl_vals[clave] = val

        # ── Timestamp última lectura ──
        self.lbl_timestamp = tk.Label(
            parent, text="Última lectura: —",
            font=("Consolas", 9),
            bg=self.COLOR_BG, fg=self.COLOR_MUTED, anchor="w"
        )
        self.lbl_timestamp.pack(fill="x", pady=(0, 8))

        # ── Sección: Alertas recientes ──
        lbl_sec2 = tk.Label(
            parent, text="⚠ ALERTAS RECIENTES",
            font=("Consolas", 10, "bold"),
            bg=self.COLOR_BG, fg=self.COLOR_MUTED, anchor="w", pady=4
        )
        lbl_sec2.pack(fill="x")

        self.txt_alertas = scrolledtext.ScrolledText(
            parent,
            height=8,
            font=("Consolas", 9),
            bg=self.COLOR_PANEL, fg=self.COLOR_AMARILLO,
            insertbackground=self.COLOR_TEXTO,
            relief="flat",
            state="disabled"
        )
        self.txt_alertas.pack(fill="both", expand=True)

    def _construir_panel_chat(self, parent):

        lbl_sec = tk.Label(
            parent, text="◈ ASISTENTE LOGÍSTICO — Claude AI",
            font=("Consolas", 10, "bold"),
            bg=self.COLOR_BG, fg=self.COLOR_MUTED, anchor="w", pady=4
        )
        lbl_sec.pack(fill="x")

        # Área de historial del chat
        self.txt_chat = scrolledtext.ScrolledText(
            parent,
            font=("Consolas", 10),
            bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO,
            insertbackground=self.COLOR_TEXTO,
            relief="flat",
            state="disabled",
            wrap="word"
        )
        self.txt_chat.pack(fill="both", expand=True, pady=(0, 8))

        # Configuramos colores para los diferentes tipos de mensaje
        self.txt_chat.tag_config("usuario",   foreground=self.COLOR_AZUL)
        self.txt_chat.tag_config("asistente", foreground=self.COLOR_VERDE)
        self.txt_chat.tag_config("sistema",   foreground=self.COLOR_MUTED)
        self.txt_chat.tag_config("error",     foreground=self.COLOR_ROJO)

        # Área de entrada de texto
        frame_entrada = tk.Frame(parent, bg=self.COLOR_BG)
        frame_entrada.pack(fill="x")

        self.entrada_chat = tk.Entry(
            frame_entrada,
            font=("Consolas", 11),
            bg=self.COLOR_PANEL, fg=self.COLOR_TEXTO,
            insertbackground=self.COLOR_TEXTO,
            relief="flat",
            highlightbackground=self.COLOR_BORDE,
            highlightthickness=1
        )
        self.entrada_chat.pack(side="left", fill="x", expand=True,
                                ipady=8, padx=(0, 8))

        # Enter también envía el mensaje
        self.entrada_chat.bind("<Return>", lambda e: self._enviar_mensaje())

        btn_enviar = tk.Button(
            frame_entrada,
            text="Enviar →",
            font=("Consolas", 10, "bold"),
            bg=self.COLOR_ACENTO, fg=self.COLOR_BG,
            activebackground=self.COLOR_AZUL,
            relief="flat", cursor="hand2",
            padx=16, pady=8,
            command=self._enviar_mensaje
        )
        btn_enviar.pack(side="right")

        # Mensaje de bienvenida
        self._agregar_mensaje_chat(
            "sistema",
            "Sistema iniciado. Puedes preguntarme sobre el estado del almacén.\n"
            "Ejemplo: '¿Hay alguna alerta activa?' o '¿Cuál es el estado del stock?'\n"
        )

    # ----------------------------------------------------------
    # ACTUALIZACIÓN AUTOMÁTICA DEL PANEL DE SENSORES
    # ----------------------------------------------------------
    def _actualizar_panel(self):
        doc = obtener_ultimo_estado()

        if doc:
            # Actualizamos cada etiqueta con su valor y color correspondiente
            self.lbl_vals["pir_texto"].config(
                text="Movimiento detectado" if doc["pir"] else "Sin movimiento",
                fg=self.COLOR_AMARILLO if doc["pir"] else self.COLOR_VERDE
            )
            self.lbl_vals["ldr_texto"].config(
                text=f"{doc['ldr']} / 1023",
                fg=self.COLOR_TEXTO
            )
            self.lbl_vals["dist_texto"].config(
                text=f"{doc['distancia_cm']} cm",
                fg=self.COLOR_TEXTO
            )
            self.lbl_vals["stock_texto"].config(
                text="OK ✓" if doc["stock_ok"] else "QUIEBRE ✗",
                fg=self.COLOR_VERDE if doc["stock_ok"] else self.COLOR_ROJO
            )
            self.lbl_vals["led_am_texto"].config(
                text="Encendido" if doc["led_amarillo"] else "Apagado",
                fg=self.COLOR_AMARILLO if doc["led_amarillo"] else self.COLOR_MUTED
            )
            self.lbl_vals["led_rj_texto"].config(
                text="Encendido" if doc["led_rojo"] else "Apagado",
                fg=self.COLOR_ROJO if doc["led_rojo"] else self.COLOR_MUTED
            )
            self.lbl_vals["servo_texto"].config(
                text=f"{doc['servo_grados']}° — "
                     f"{'CERRADA' if doc['servo_grados'] == 90 else 'abierta'}",
                fg=self.COLOR_ROJO if doc["servo_grados"] == 90 else self.COLOR_VERDE
            )
            self.lbl_vals["buzz_texto"].config(
                text="ACTIVO ♪" if doc["buzzer"] else "Silencio",
                fg=self.COLOR_ROJO if doc["buzzer"] else self.COLOR_MUTED
            )

            ts = doc["timestamp"]
            if isinstance(ts, datetime):
                ts = ts.strftime("%Y-%m-%d %H:%M:%S")
            self.lbl_timestamp.config(text=f"Última lectura: {ts}")

            # Actualizamos el panel de alertas
            alertas = list(col_alert.find(
                sort=[("timestamp", pymongo.DESCENDING)],
                limit=10
            ))
            self.txt_alertas.config(state="normal")
            self.txt_alertas.delete("1.0", "end")
            if alertas:
                for a in alertas:
                    ts_a = a["timestamp"]
                    if isinstance(ts_a, datetime):
                        ts_a = ts_a.strftime("%H:%M:%S")
                    self.txt_alertas.insert(
                        "end",
                        f"[{ts_a}] {a['tipo']}\n{a['mensaje']}\n\n"
                    )
            else:
                self.txt_alertas.insert("end", "Sin alertas registradas.")
            self.txt_alertas.config(state="disabled")

        # Volvemos a llamar esta función en 2000ms (bucle de actualización)
        self.root.after(2000, self._actualizar_panel)

    # ----------------------------------------------------------
    # MANEJO DEL CHAT CON EL LLM
    # ----------------------------------------------------------
    def _enviar_mensaje(self):
        pregunta = self.entrada_chat.get().strip()
        if not pregunta:
            return

        # Limpiamos el campo de entrada
        self.entrada_chat.delete(0, "end")

        # Mostramos la pregunta del usuario en el chat
        self._agregar_mensaje_chat("usuario", f"Tú: {pregunta}\n")

        # Mostramos indicador de que está pensando
        self._agregar_mensaje_chat("sistema", "Consultando al asistente...\n")

        # Ejecutamos la llamada al LLM en un hilo separado
        # para no congelar la interfaz mientras espera la respuesta
        hilo = threading.Thread(
            target=self._obtener_respuesta_llm,
            args=(pregunta,),
            daemon=True
        )
        hilo.start()

    def _obtener_respuesta_llm(self, pregunta):
        try:
            respuesta = consultar_llm(pregunta)

            # Actualizamos la interfaz desde el hilo principal
            self.root.after(0, lambda: self._mostrar_respuesta(respuesta))

        except Exception as e:
            self.root.after(
                0,
                lambda: self._agregar_mensaje_chat(
                    "error",
                    f"Error al consultar el asistente: {e}\n"
                    "Verifica tu API key en el código.\n"
                )
            )

    def _mostrar_respuesta(self, respuesta):
        # Borramos el "Consultando..." y mostramos la respuesta real
        self.txt_chat.config(state="normal")
        contenido = self.txt_chat.get("1.0", "end")
        idx = contenido.rfind("Consultando al asistente...")
        if idx != -1:
            # Calculamos la posición en términos de línea.columna de Tkinter
            linea = contenido[:idx].count("\n") + 1
            self.txt_chat.delete(f"{linea}.0", f"{linea}.end+1c")
        self.txt_chat.config(state="disabled")

        self._agregar_mensaje_chat("asistente", f"Asistente: {respuesta}\n\n")

    def _agregar_mensaje_chat(self, tipo, texto):
        self.txt_chat.config(state="normal")
        self.txt_chat.insert("end", texto, tipo)
        self.txt_chat.see("end")  # Auto-scroll al final
        self.txt_chat.config(state="disabled")


# ============================================================
# PUNTO DE ENTRADA
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app  = InterfazWarehouse(root)
    root.mainloop()