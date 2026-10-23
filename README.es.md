# ☕ AI Basic Inventory Agent Loop

Un sistema de gestión de inventario impulsado por IA para una tienda de suministros de cafetería con dos ubicaciones físicas. Construido con **FastAPI** y un **bucle de agente de IA manual** — sin frameworks.

Carla, la dueña de la cafetería, puede hablar con el sistema de forma natural — registrar entregas, registrar ventas y consultar los niveles de stock — todo a través de una interfaz CLI conversacional.

---

## Cómo Funciona

El sistema tiene dos partes que trabajan juntas:

### 1. API REST (`api/app.py`)
Servidor FastAPI que gestiona los datos de inventario almacenados en un archivo `products.csv` para que todo persista entre sesiones.

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/inventory` | GET | Lista todos los productos con sus IDs, nombres, cantidades y unidades |
| `/inventory` | POST | Agrega un nuevo producto (nombre, cantidad, unidad) → devuelve 201 |
| `/inventory/{id}` | PATCH | Actualiza el stock usando un delta (+ para entradas, − para salidas) |
| `/inventory/alerts` | GET | Obtiene productos por debajo de un umbral configurable (por defecto: 10) |

### 2. Agente de IA (`agent.py`)
Un agente de Python que se conecta a un LLM (API compatible con OpenAI) y utiliza los endpoints REST como **herramientas**. El agente ejecuta un **bucle manual** — sin LangChain, sin LlamaIndex, sin frameworks:

```
Observar (leer la entrada del usuario)
  → Pensar (enviar al LLM con definiciones de herramientas)
    → Actuar (llamar a la herramienta que seleccionó el LLM)
      → Actualizar (inyectar el resultado de nuevo en el contexto)
        → Repetir hasta que el LLM dé una respuesta final
```

#### Herramientas disponibles para el LLM

| Herramienta | Descripción |
|------|-------------|
| `list_products` | Ver todos los productos del inventario |
| `add_product` | Registrar un nuevo producto (nombre, cantidad, unidad) |
| `update_stock` | Actualizar stock por ID del producto (+delta = recibido, −delta = vendido) |
| `check_low_stock` | Encontrar productos por debajo de un umbral de cantidad |

### Registro de Conversación
Cada evento del bucle se agrega a `conversation_log.csv` con cuatro campos:

| Campo | Descripción |
|-------|-------------|
| `actor` | `user` (usuario), `agent` (agente) o `tool` (herramienta) |
| `message` | El texto o resultado del evento |
| `tool_call` | Nombre de la herramienta llamada (vacío si no aplica) |
| `timestamp` | Fecha/hora ISO 8601 del evento |

El archivo es **solo de añadido** — cada sesión agrega filas sin sobrescribir las sesiones anteriores.

---

## Estructura del Proyecto

```
.
├── agent.py                 # Agente de IA con bucle de agente manual
├── api/
│   ├── __init__.py          # Marcador del paquete API
│   └── app.py               # Aplicación FastAPI
├── products.csv             # Datos de inventario (persistentes, leídos/escritos por la API)
├── conversation_log.csv     # Registro de conversación (solo añadido, auto-generado)
├── requirements.txt         # Dependencias de Python
├── .env                     # Configuración de entorno
├── .gitignore               # Archivos ignorados
└── README.md                # Este archivo
```

---

## Configuración (Setup)

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

Esto instala **fastapi**, **uvicorn**, **httpx**, **pydantic** y **python-dotenv**.

### 2. Crear o editar `.env`

El proyecto usa un archivo `.env` para la configuración. Crea uno con las siguientes variables:

```env
# Configuración del LLM (API compatible con OpenAI)
LLM_API_KEY=tu_api_key_aqui
LLM_BASE_URL=https://llm.4geeks.ai
LLM_MODEL=online/openrouter/openai/gpt-6-luna

# API de Inventario
API_BASE_URL=http://localhost:8000
```

Puedes apuntar a cualquier endpoint compatible con OpenAI (OpenAI, OpenRouter, Groq, Ollama local, etc.).

### 3. Datos iniciales (opcional)

El proyecto incluye un `products.csv` con 15 artículos de cafetería listos para usar. Puedes editarlo directamente o agregar productos a través del agente.

---

## Cómo Ejecutar (Instrucciones de ejecución)

### Paso 1 — Iniciar la API

Abre una **primera terminal** y lanza el servidor FastAPI:

```bash
uvicorn api.app:APP --reload --host 0.0.0.0 --port 8000
```

La API estará disponible en `http://localhost:8000`. Deberías ver:

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Paso 2 — Iniciar el agente

En una **segunda terminal**, ejecuta el agente:

```bash
python agent.py
```

El agente te saludará:

```
☕ Coffee Shop Inventory Agent
========================================
Type your message to Carla's assistant, or type 'exit' / 'quit' to stop.
```

### Paso 3 — Habla con el asistente de Carla

Escribe mensajes en lenguaje natural. El agente acepta mensajes en inglés como los ejemplos, o puedes intentar en español. Aquí hay ejemplos de todo lo que el sistema puede hacer:

#### 📋 Listar todos los productos
```
You: show me all products in inventory
```
→ Devuelve una tabla con todos los productos y sus IDs, nombres, cantidades y unidades.

#### ⚠️ Consultar alertas de stock bajo
```
You: what products are running low?
```
→ Devuelve todos los productos con cantidad por debajo del umbral por defecto (10).

#### 📦 Registrar una entrega (stock entrante)
```
You: we just received 30 units of oat milk
```
→ El agente busca Oat Milk, encuentra su ID y actualiza el stock con +30.

#### 💰 Registrar una venta (stock saliente)
```
You: we sold 12 bags of arabica today
```
→ El agente encuentra "Arabica Coffee - Single Origin" y actualiza el stock con −12.

#### 🆕 Agregar un nuevo producto
```
You: add a new product: coconut milk, 20 liters
```
→ Crea una nueva entrada de producto en el inventario.

#### ❌ Detener la sesión
```
You: exit
```
o `quit` / `q` para salir.

---

## Notas de Desarrollo

### Diseño de la API
- Los productos tienen un `id` entero auto-incremental
- Las actualizaciones de stock usan un valor **delta**: positivo para stock entrante, negativo para saliente
- La API valida que el stock nunca sea negativo (devuelve HTTP 400 si lo fuera)
- Todos los endpoints devuelven mensajes de error descriptivos y códigos de estado HTTP adecuados

### Diseño del Agente
- El bucle del agente está implementado desde cero en Python puro (~280 líneas)
- El historial de conversación se mantiene en memoria durante una sesión para razonamiento contextual
- El bucle termina limpiamente cuando el LLM devuelve una respuesta final sin llamadas pendientes
- Un límite de seguridad de 10 iteraciones previene bucles infinitos
- El agente lee `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL` y `API_BASE_URL` del entorno

### Registro de Conversación
- Cada mensaje del usuario, respuesta del agente, llamada de herramienta y resultado se registra en `conversation_log.csv`
- El CSV usa cuatro campos: `actor`, `message`, `tool_call`, `timestamp`
- Las nuevas sesiones añaden al archivo existente (nunca sobrescribe)

---

## Resultados de las Pruebas

El sistema se probó de extremo a extremo con los tres escenarios principales:

| Escenario | Entrada | Resultado |
|----------|---------|-----------|
| 📋 Listar productos | `show me all products in inventory` | ✅ Devuelve la tabla de 15 productos |
| ⚠️ Alertas de stock bajo | `what products are running low?` | ✅ Identificó 5 productos por debajo del umbral |
| 📦 Registrar entrega | `we just received 30 units of oat milk` | ✅ Encontró el producto (ID 1), actualizó 24 → 54 liters |
| 🆕 Agregar producto | `add coconut milk, 20 liters` | ✅ Creó un nuevo producto con ID 16 |
| 📝 Registro de conversación | (automático) | ✅ 14+ entradas registradas en todos los campos |

El agente correctamente:
- Interpretó lenguaje natural en llamadas de herramientas estructuradas
- Llamó `list_products` primero para encontrar IDs de productos antes de `update_stock`
- Manejó errores con elegancia (por ejemplo, previno stock negativo)
- Mantuvo el contexto de conversación en múltiples intercambios
