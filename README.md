# OneCoreMxPy

API REST con FastAPI para gestión de archivos CSV, **análisis de documentos con IA** y autenticación JWT, almacenamiento en S3 (LocalStack) y SQL Server.

## 🚀 Características

- **Autenticación JWT**: Login, registro y renovación de tokens
- **Roles de usuario**: user, uploader, admin
- **Subida de archivos CSV**: Con validación automática
- **Almacenamiento S3**: Usando LocalStack para desarrollo local
- **Base de datos**: SQL Server LocalDB
- **📄 Análisis de Documentos con IA**: Clasificación y extracción automática
- **📜 Módulo Histórico**: Registro de eventos con filtros y exportación Excel

## 🆕 Módulos Web

### 📄 Módulo de Análisis de Documentos

Interfaz web para subir documentos (PDF, JPG, PNG) con análisis automático por IA:

#### Clasificación Automática
- **Factura**: Documentos con datos económicos/financieros
- **Información**: Documentos con texto general

#### Extracción de Datos

**Para Facturas:**
- Cliente (nombre y dirección)
- Proveedor (nombre y dirección)
- Número de factura, fecha
- Productos (cantidad, nombre, precio unitario, total)
- Total de la factura

**Para Documentos Informativos:**
- Descripción y resumen del contenido
- Análisis de sentimiento (positivo, negativo, neutral)
- Temas clave detectados

### 📜 Módulo Histórico

Pantalla para visualizar el registro de eventos del sistema:

- **Registros**: ID, Tipo, Descripción, Fecha y hora
- **Tipos de eventos**: Subida de documento, Análisis IA, Interacción usuario, Sistema
- **Filtros**: Por tipo, descripción o rango de fechas
- **Exportación**: Descarga en formato Excel

## 📋 Requisitos

- Python 3.11+
- Docker (para LocalStack)
- SQL Server LocalDB
- ODBC Driver 17 for SQL Server

## 🛠️ Instalación

### 1. Clonar y configurar entorno virtual

```powershell
cd d:\Code\OneCoreMxPy
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copiar `.env.example` a `.env` y ajustar los valores:

```powershell
Copy-Item .env.example .env
```

### 3. Iniciar LocalStack (S3)

```powershell
docker-compose up -d
```

### 4. Crear base de datos en LocalDB

```powershell
# Conectar a LocalDB y crear la base de datos
SqlLocalDB.exe create "MSSQLLocalDB" -s
sqlcmd -S "(localdb)\MSSQLLocalDB" -Q "CREATE DATABASE OneCoreMxPy"
```

### 5. Iniciar la aplicación

```powershell
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 Documentación API

Una vez iniciada la aplicación:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🔑 Endpoints Principales

### Autenticación

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Iniciar sesión |
| POST | `/api/v1/auth/register` | Registrar usuario |
| POST | `/api/v1/auth/refresh` | Renovar token |
| GET | `/api/v1/auth/me` | Información del usuario actual |

### Archivos

| Método | Endpoint | Descripción | Rol Requerido |
|--------|----------|-------------|---------------|
| POST | `/api/v1/files/upload` | Subir archivo CSV | uploader |
| GET | `/api/v1/files/` | Listar archivos | user |
| GET | `/api/v1/files/{id}` | Obtener archivo | user |
| GET | `/api/v1/files/{id}/validations` | Ver validaciones | user |

### Documentos (Análisis IA)

| Método | Endpoint | Descripción | Rol Requerido |
|--------|----------|-------------|---------------|
| POST | `/api/v1/documents/upload` | Subir y analizar documento | uploader |
| GET | `/api/v1/documents/` | Listar documentos | user |
| GET | `/api/v1/documents/{id}` | Obtener detalle del documento | user |
| DELETE | `/api/v1/documents/{id}` | Eliminar documento | uploader |
| POST | `/api/v1/documents/{id}/reanalyze` | Re-analizar documento | uploader |
| GET | `/api/v1/documents/{id}/download` | Descargar documento original | user |

### Histórico de Eventos

| Método | Endpoint | Descripción | Rol Requerido |
|--------|----------|-------------|---------------|
| GET | `/api/v1/events/` | Listar eventos (con filtros) | user |
| GET | `/api/v1/events/{id}` | Obtener detalle del evento | user |
| GET | `/api/v1/events/types` | Listar tipos de eventos | user |
| GET | `/api/v1/events/stats` | Estadísticas de eventos | user |
| GET | `/api/v1/events/export` | Exportar a Excel | admin |

### Interfaz Web

| URL | Descripción |
|-----|-------------|
| `/web/login` | Página de inicio de sesión |
| `/web/documents` | Módulo de análisis de documentos |
| `/web/events` | Módulo histórico de eventos |

## 📁 Estructura del Proyecto

```
OneCoreMxPy/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entrada principal FastAPI
│   ├── api/
│   │   ├── __init__.py
│   │   ├── auth.py          # Endpoints de autenticación
│   │   ├── files.py         # Endpoints de archivos CSV
│   │   ├── documents.py     # Endpoints de análisis de documentos
│   │   ├── events.py        # Endpoints de histórico
│   │   └── web.py           # Rutas de interfaz web
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Configuración con Pydantic
│   │   ├── database.py      # Conexión a SQL Server
│   │   └── security.py      # JWT y autenticación
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py        # Modelos SQLAlchemy
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py       # Schemas Pydantic
│   ├── services/
│   │   ├── __init__.py
│   │   ├── csv_service.py       # Validación de CSV
│   │   ├── s3_service.py        # Operaciones S3
│   │   ├── document_service.py  # Análisis de documentos con IA
│   │   └── event_service.py     # Gestión de eventos
│   └── templates/
│       ├── base.html            # Template base
│       ├── login.html           # Página de login
│       ├── documents.html       # Módulo de documentos
│       └── events.html          # Módulo histórico
├── tests/
│   ├── test_document_service.py
│   └── test_event_service.py
├── .env                     # Variables de entorno (no commitear)
├── .env.example             # Ejemplo de variables
├── docker-compose.yml       # LocalStack
├── requirements.txt         # Dependencias Python
└── README.md
```

## 🧪 Ejemplo de Uso

### 1. Registrar un usuario con rol uploader

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "uploader1", "password": "password123", "role": "uploader"}'
```

### 2. Iniciar sesión

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=uploader1&password=password123"
```

### 3. Subir archivo CSV

```bash
curl -X POST "http://localhost:8000/api/v1/files/upload" \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@archivo.csv" \
  -F "param1=valor1" \
  -F "param2=valor2"
```

### 4. Renovar token

```bash
curl -X POST "http://localhost:8000/api/v1/auth/refresh" \
  -H "Authorization: Bearer <TOKEN>"
```

## ⚙️ Configuración

Variables de entorno disponibles en `.env`:

| Variable | Descripción | Valor por defecto |
|----------|-------------|-------------------|
| `APP_NAME` | Nombre de la aplicación | OneCoreMxPy |
| `DEBUG` | Modo debug | true |
| `JWT_SECRET_KEY` | Clave secreta para JWT | (requerido) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Duración del token | 30 |
| `DB_SERVER` | Servidor SQL | (localdb)\MSSQLLocalDB |
| `DB_NAME` | Nombre de base de datos | OneCoreMxPy |
| `S3_ENDPOINT_URL` | URL de LocalStack | http://localhost:4566 |
| `S3_BUCKET_NAME` | Nombre del bucket S3 | onecoremxpy-bucket |
| `OPENAI_API_KEY` | API Key de OpenAI (para análisis IA) | (opcional) |
| `OPENAI_MODEL` | Modelo de OpenAI | gpt-4o |
| `DOCUMENT_ALLOWED_EXTENSIONS` | Extensiones de documentos | pdf,jpg,jpeg,png |
| `MAX_DOCUMENT_SIZE_MB` | Tamaño máximo de documento | 20 |

## 📝 Validaciones de CSV

El sistema valida automáticamente:

- **empty_value**: Valores vacíos en celdas
- **incorrect_type**: Tipos de datos incorrectos
- **duplicate**: Filas duplicadas
- **structure_error**: Errores de estructura del archivo
- **suspicious_content**: Contenido potencialmente peligroso

## 🔒 Seguridad

- Contraseñas hasheadas con bcrypt
- Tokens JWT firmados con HS256
- Validación de roles en endpoints protegidos
- Sanitización de contenido CSV

## 📄 Licencia

MIT
