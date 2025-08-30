# 🚀 HB API - API Pública de HomeBroker

API REST completamente **PÚBLICA** para obtener datos en tiempo real de HomeBroker, incluyendo opciones, acciones, bonos, cedears y más.

## ✨ Características Principales

- **🔓 API 100% PÚBLICA** - Sin autenticación requerida
- **📊 Datos en tiempo real** de opciones, acciones y securities
- **🐳 Despliegue fácil** en Render, VPS o local
- **⚡ FastAPI** - Framework moderno y rápido
- **🔄 Reconexión automática** y monitoreo de salud

## 🚀 Despliegue Rápido

### 🌐 Opción 1: Render (Recomendado para principiantes)

Render es una plataforma gratuita que permite desplegar aplicaciones web fácilmente.

#### Pasos para Render:

1. **Fork este repositorio** en tu cuenta de GitHub
2. **Ve a [render.com](https://render.com)** y crea una cuenta
3. **Crea un nuevo Web Service**
4. **Conecta tu repositorio** de GitHub
5. **Configura las variables de entorno:**

```bash
HB_BROKER=0
HB_DNI=tu_dni_aqui
HB_USER=tu_usuario_aqui
HB_PASSWORD=tu_password_aqui
HB_OPTIONS_PREFIXES=GFG,GAL
HB_STOCK_PREFIXES=GGAL,YPFD,PAMP
HB_TICKERS_FILE=tickers.json
HB_RECONNECT_INTERVAL=30
HB_MAX_RECONNECT_ATTEMPTS=5
HB_HEALTH_CHECK_INTERVAL=60
```

6. **Build Command:** `pip install -r requirements.txt`
7. **Start Command:** `python api.py`
8. **¡Listo!** Tu API estará disponible en `https://tu-app.onrender.com`

### 🖥️ Opción 2: VPS con Docker (Para usuarios avanzados)

Si prefieres control total sobre tu servidor, puedes usar un VPS con Docker.

#### Requisitos del VPS:

- **Sistema:** Ubuntu 20.04+ o similar
- **RAM:** Mínimo 1GB (recomendado 2GB+)
- **CPU:** 1 vCPU mínimo
- **Almacenamiento:** 10GB mínimo

#### Instalación en VPS:

1. **Conecta a tu VPS:**

```bash
ssh usuario@tu-vps-ip
```

2. **Instala Docker y Docker Compose:**

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Agregar usuario al grupo docker
sudo usermod -aG docker $USER

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Reiniciar sesión para aplicar cambios
exit
# Reconectar: ssh usuario@tu-vps-ip
```

3. **Clona el repositorio:**

```bash
git clone https://github.com/tu-usuario/api-market-publico.git
cd api-market-publico
```

4. **Configura las variables de entorno:**

```bash
cp env.example .env
nano .env
# Edita con tus credenciales de HomeBroker
```

5. **Levanta la aplicación:**

```bash
docker-compose up -d
```

6. **Verifica que esté funcionando:**

```bash
curl http://localhost:8080/health
```

7. **Configura firewall (opcional):**

```bash
sudo ufw allow 8080
```

## 📋 Endpoints Disponibles

### 🔍 Endpoints Públicos (Sin Autenticación)

| Endpoint      | Descripción               | Ejemplo           |
| ------------- | ------------------------- | ----------------- |
| `/`           | Información de la API     | `GET /`           |
| `/health`     | Estado de conexión        | `GET /health`     |
| `/options`    | Todas las opciones        | `GET /options`    |
| `/stocks`     | Todas las acciones        | `GET /stocks`     |
| `/securities` | Todos los securities      | `GET /securities` |
| `/cauciones`  | Datos de cauciones        | `GET /cauciones`  |
| `/config`     | Configuración del sistema | `GET /config`     |

### 📊 Ejemplos de Uso

#### Obtener todas las acciones:

```bash
curl "https://tu-api.onrender.com/stocks"
```

#### Obtener opciones por prefijo:

```bash
curl "https://tu-api.onrender.com/options/prefix/GFG"
```

#### Obtener securities por ticker:

```bash
curl "https://tu-api.onrender.com/securities/ticker/GGAL"
```

#### Obtener estado de conexión:

```bash
curl "https://tu-api.onrender.com/health"
```

## ⚙️ Configuración

### Variables de Entorno Principales

```bash
# Credenciales de HomeBroker (OBLIGATORIAS)
HB_BROKER=0                    # ID del broker (0 = IOL)
HB_DNI=tu_dni_aqui            # Tu DNI
HB_USER=tu_usuario_aqui       # Tu usuario
HB_PASSWORD=tu_password_aqui  # Tu contraseña

# Configuración de instrumentos (OPCIONALES)
HB_OPTIONS_PREFIXES=GFG,GAL   # Prefijos de opciones
HB_STOCK_PREFIXES=GGAL,YPFD   # Prefijos de acciones
HB_TICKERS_FILE=tickers.json  # Archivo de configuración

# Configuración de reconexión (OPCIONALES)
HB_RECONNECT_INTERVAL=30      # Intervalo de reconexión (segundos)
HB_MAX_RECONNECT_ATTEMPTS=5   # Máximo de intentos
HB_HEALTH_CHECK_INTERVAL=60   # Intervalo de health check
```

### Archivo tickers.json

```json
{
  "options_prefixes": ["GFG", "YPF", "PAMP"],
  "stock_prefixes": ["GGAL", "YPFD", "PAMP"],
  "acciones": ["GGAL", "YPFD", "PAMP"],
  "bonos": ["AL30", "GD30"],
  "cedears": ["AAPL", "TSLA", "MSFT"]
}
```

## 🛠️ Desarrollo Local

### Instalación de Dependencias

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/api-market-publico.git
cd api-market-publico

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp env.example .env
# Editar .env con tus credenciales

# Ejecutar API
python api.py
```

### Estructura del Proyecto

```
api-market-publico/
├── api.py                 # API principal (FastAPI)
├── hb_service.py         # Servicio de HomeBroker
├── docker-compose.yml    # Configuración de Docker
├── Dockerfile            # Imagen de Docker
├── requirements.txt      # Dependencias de Python
├── tickers.json         # Configuración de instrumentos
├── env.example          # Variables de entorno de ejemplo
└── README.md            # Este archivo
```

## 🔧 Solución de Problemas

### Error de Conexión

- Verifica que las credenciales sean correctas
- Asegúrate de que tu broker esté activo
- Revisa el endpoint `/health` para el estado de conexión

### Error de Dependencias

- Asegúrate de tener Python 3.8+
- Reinstala las dependencias: `pip install -r requirements.txt`
- Verifica que pyhomebroker esté instalado correctamente

### Error en Docker

- Verifica que Docker esté ejecutándose
- Revisa los logs: `docker-compose logs`
- Reinicia el contenedor: `docker-compose restart`

## 📚 Recursos Adicionales

- **Documentación de la API:** `https://tu-api.onrender.com/docs`
- **FastAPI:** [fastapi.tiangolo.com](https://fastapi.tiangolo.com)
- **pyhomebroker:** [PyPI](https://pypi.org/project/pyhomebroker/)
- **Render:** [render.com](https://render.com)

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Si encuentras un bug o tienes una sugerencia:

1. Fork el repositorio
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📄 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

---

**⚠️ Importante:** Esta API es completamente pública. No incluyas credenciales reales en el código. Usa variables de entorno para configurar tus credenciales de HomeBroker.
