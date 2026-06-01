#include <Servo.h>

// ============================================================
// CONFIGURACIÓN DE PINES (HARDWARE)
// ============================================================
const int PIN_PIR      = 2;   // Sensor de Movimiento
const int PIN_TRIG     = 3;   // Trigger del Ultrasonido
const int PIN_ECHO     = 4;   // Echo del Ultrasonido
const int PIN_BUZZER   = 5;   // Zumbador / Altavoz
const int PIN_LED_ROJO = 6;   // LED Alerta (Quiebre Stock)
const int PIN_LDR      = A0;  // Fotorresistencia (Sensor Luz)
const int PIN_LED_AMAR = 8;   // LED Pasillo (Iluminación)
const int PIN_SERVO    = 9;   // Servomotor de la Barrera

// ============================================================
// CALIBRACIÓN DE UMBRALES
// ============================================================
const int  UMBRAL_LDR       = 300; // OJO: Si con tu luz normal se prende solo, sube este número a 500 o 600
const long UMBRAL_DISTANCIA = 12;  // Distancia en cm hasta la pared de la maqueta

// Variables globales del sistema
bool hayMovimiento   = false;
bool estaOscuro      = false;
bool hayQuiebreStock = false;
int  lecturaLDR      = 0;
long distanciaCm     = 0;

Servo servoBarrera;

// ============================================================
// SECCIÓN DE SONIDOS ICÓNICOS (RETRO-GAMING 8-BITS)
// ============================================================

void tocarArranque() {
  // 🎶 SONIDO 1: ¡Secreto Descubierto! - The Legend of Zelda
  // Suena una única vez al conectar el Arduino para indicar sistema OK.
  int notas[] = {784, 740, 622, 440, 415, 659, 831, 1047};
  int duraciones[] = {100, 100, 100, 100, 100, 100, 100, 300};
  
  for (int i = 0; i < 8; i++) {
    tone(PIN_BUZZER, notas[i], duraciones[i]);
    delay(duraciones[i] + 20);
  }
  noTone(PIN_BUZZER);
}

void tocarBienvenida() {
  // 🎶 SONIDO 2: ¡Moneda de Super Mario Bros!
  // Suena cuando un operario camina de noche y el stock está correcto.
  tone(PIN_BUZZER, 988, 80);   delay(90);
  tone(PIN_BUZZER, 1319, 250); delay(260);
  noTone(PIN_BUZZER);
}

void tocarAlertaSola() {
  // 🎶 SONIDO 3: Muerte de Pac-Man (Caída digital)
  // Suena en el instante exacto en que se retira el stock del estante.
  for (int frec = 1000; frec > 150; frec -= 60) {
    tone(PIN_BUZZER, frec, 30);
    delay(35);
  }
  tone(PIN_BUZZER, 110, 200); delay(220); 
  noTone(PIN_BUZZER);
}

void tocarEmergencia() {
  // 🎶 SONIDO 4: Marcha Imperial - Star Wars
  // ¡Alerta máxima! Hay quiebre de stock e invasión de pasillo al tiempo.
  tone(PIN_BUZZER, 440, 350); delay(400);
  tone(PIN_BUZZER, 440, 350); delay(400);
  tone(PIN_BUZZER, 440, 350); delay(400);
  tone(PIN_BUZZER, 349, 250); delay(300);
  tone(PIN_BUZZER, 523, 150); delay(180);
  tone(PIN_BUZZER, 440, 350); delay(400);
  noTone(PIN_BUZZER);
}

// ============================================================
// CONFIGURACIÓN INICIAL (SETUP)
// ============================================================
void setup() {
  Serial.begin(9600);
  pinMode(PIN_PIR,      INPUT);
  pinMode(PIN_TRIG,     OUTPUT);
  pinMode(PIN_ECHO,     INPUT);
  pinMode(PIN_LED_ROJO, OUTPUT);
  pinMode(PIN_LED_AMAR, OUTPUT);
  
  // Inicialización segura del Servomotor
  servoBarrera.attach(PIN_SERVO);
  servoBarrera.write(0); // Forzar barrera abierta al iniciar
  delay(200);
  
  tocarArranque(); // Melodía de Zelda al encender
  Serial.println("SISTEMA_INICIADO");
  delay(1000);
}

// ============================================================
// FUNCIÓN: MUESTRAS DE ULTRASONIDO (HC-SR04)
// ============================================================
long medirDistancia() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);
  long duracion = pulseIn(PIN_ECHO, HIGH, 30000);
  long cm = (duracion * 0.0343) / 2;
  return cm;
}

int estadoSonidoAnterior = -1;

// ============================================================
// SISTEMA DE CONTROL AUTOMATIZADO
// ============================================================
void controlarSistema() {
  // 1. Control de Iluminación Inteligente Eficiente
  if (hayMovimiento && estaOscuro) {
    digitalWrite(PIN_LED_AMAR, HIGH);
  } else {
    digitalWrite(PIN_LED_AMAR, LOW);
  }

  // 2. Control de Actuadores de Seguridad (Físicos)
  if (hayQuiebreStock) {
    servoBarrera.write(90); // Cierra barrera física
    digitalWrite(PIN_LED_ROJO, HIGH);
  } else {
    servoBarrera.write(0);  // Abre barrera física
    digitalWrite(PIN_LED_ROJO, LOW);
  }

  // 3. Máquina de Estados Acústica (Previene bucles infinitos de sonido)
  int estadoActual = 0;
  if      ( hayQuiebreStock &&  hayMovimiento) estadoActual = 3; // Emergencia total
  else if ( hayQuiebreStock && !hayMovimiento) estadoActual = 2; // Alerta Almacén Vacío
  else if (!hayQuiebreStock &&  hayMovimiento) estadoActual = 1; // Flujo Peatonal Normal
  else                                         estadoActual = 0; // Estado de Reposo

  if (estadoActual != estadoSonidoAnterior) {
    if      (estadoActual == 3) tocarEmergencia();
    else if (estadoActual == 2) tocarAlertaSola();
    else if (estadoActual == 1) tocarBienvenida();
    else                        noTone(PIN_BUZZER);
    estadoSonidoAnterior = estadoActual; // Bloquea el sonido hasta el próximo cambio
  }
}

// ============================================================
// ENVÍO DE DATOS HACIA EL BACKEND EN PYTHON
// ============================================================
void enviarDatosSerial() {
  // Mantener estrictamente este formato para evitar romper el script backend.py
  Serial.print("PIR:");        Serial.print(hayMovimiento ? 1 : 0);
  Serial.print(",LDR:");       Serial.print(lecturaLDR);
  Serial.print(",DIST:");      Serial.print(distanciaCm);
  Serial.print(",STOCK:");     Serial.print(hayQuiebreStock ? 0 : 1);
  Serial.print(",LED_AMAR:");  Serial.print(hayMovimiento && estaOscuro ? 1 : 0);
  Serial.print(",LED_ROJO:");  Serial.print(hayQuiebreStock ? 1 : 0);
  Serial.print(",SERVO:");     Serial.print(hayQuiebreStock ? 90 : 0);
  Serial.print(",BUZZ:");      Serial.println(hayQuiebreStock ? 1 : 0);
}

// ============================================================
// BUCLE PRINCIPAL (LOOP)
// ============================================================
void loop() {
  // Lectura de los componentes de entrada
  hayMovimiento = digitalRead(PIN_PIR);
  lecturaLDR    = analogRead(PIN_LDR);
  
  // LÓGICA DE LUZ: Si el número en tu consola SUBE al tapar el sensor con tu dedo, usa el signo (>)
  // Si el número BAJA al tapar el sensor con tu dedo, cambia el signo por (<)
  estaOscuro    = (lecturaLDR > UMBRAL_LDR);

  distanciaCm = medirDistancia();
  if (distanciaCm > 0) {
    // CORRECCIÓN MATEMÁTICA: Si mide la pared (12cm o más), es Quiebre de Stock definitivo
    hayQuiebreStock = (distanciaCm >= UMBRAL_DISTANCIA);
  }

  controlarSistema();   // Procesa alarmas, luces y motores
  enviarDatosSerial();  // Reporta por USB a Python y MongoDB
  delay(500);           // Muestreo estable cada medio segundo
}