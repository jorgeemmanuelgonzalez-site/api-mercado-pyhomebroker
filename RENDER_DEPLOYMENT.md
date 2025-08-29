# 🚀 Despliegue en Render - HB API

Guía paso a paso para desplegar la HB API en Render de forma gratuita.

## 📋 Prerrequisitos

- ✅ Cuenta de GitHub
- ✅ Cuenta en [Render.com](https://render.com)
- ✅ Credenciales de HomeBroker (DNI, usuario, contraseña)

## 🔧 Pasos para el Despliegue

### 1. Fork del Repositorio

1. Ve a este repositorio en GitHub
2. Haz clic en **"Fork"** en la esquina superior derecha
3. Selecciona tu cuenta de GitHub
4. Espera a que se complete el fork

### 2. Crear Cuenta en Render

1. Ve a [render.com](https://render.com)
2. Haz clic en **"Get Started"**
3. Selecciona **"Continue with GitHub"**
4. Autoriza a Render a acceder a tu cuenta de GitHub

### 3. Crear Nuevo Web Service

1. En el dashboard de Render, haz clic en **"New +"**
2. Selecciona **"Web Service"**
3. Haz clic en **"Connect a repository"**
4. Selecciona tu repositorio fork de `api-market-publico`

### 4. Configurar el Servicio

#### Configuración Básica:
- **Name:** `hb-api` (o el nombre que prefieras)
- **Environment:** `Python 3`
- **Region:** Selecciona la más cercana a tu ubicación
- **Branch:** `main` (o `master`)
- **Root Directory:** Dejar vacío (por defecto)

#### Build & Deploy:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python api.py`

### 5. Configurar Variables de Entorno

En la sección **"Environment Variables"**, agrega:

```bash
# CREDENCIALES OBLIGATORIAS (cambiar por tus datos reales)
HB_DNI=tu_dni_real_aqui
HB_USER=tu_usuario_real
HB_PASSWORD=tu_password_real

# CONFIGURACIÓN OPCIONAL (puedes dejar los valores por defecto)
HB_BROKER=0
HB_OPTIONS_PREFIXES=GFG,GAL
HB_STOCK_PREFIXES=GGAL,YPFD,PAMP
HB_TICKERS_FILE=tickers.json
HB_RECONNECT_INTERVAL=30
HB_MAX_RECONNECT_ATTEMPTS=5
HB_HEALTH_CHECK_INTERVAL=60
```

**⚠️ IMPORTANTE:** 
- `HB_DNI`, `HB_USER` y `HB_PASSWORD` son **OBLIGATORIOS**
- Los demás valores son opcionales y tienen valores por defecto
- **NUNCA** subas credenciales reales al código

### 6. Desplegar

1. Haz clic en **"Create Web Service"**
2. Render comenzará a construir y desplegar tu aplicación
3. El proceso puede tomar 5-10 minutos
4. Verás el progreso en tiempo real

### 7. Verificar el Despliegue

Una vez completado:

1. Haz clic en la URL generada (ej: `https://tu-app.onrender.com`)
2. Deberías ver la respuesta de la API:
```json
{
  "message": "HB API funcionando",
  "version": "1.0.0",
  "endpoints": {...},
  "authentication": "API PÚBLICA - No se requiere autenticación"
}
```

3. Prueba el endpoint de salud: `https://tu-app.onrender.com/health`

## 🔍 Solución de Problemas

### Error de Build
- Verifica que el `requirements.txt` esté presente
- Asegúrate de que Python 3.8+ esté seleccionado
- Revisa los logs de build en Render

### Error de Inicio
- Verifica que las credenciales de HomeBroker sean correctas
- Revisa los logs de runtime en Render
- Asegúrate de que el broker esté activo

### Error de Conexión
- Verifica que las variables de entorno estén configuradas
- Revisa el endpoint `/health` para el estado de conexión
- Espera unos minutos para que se establezca la conexión

## 📊 Monitoreo

### Logs en Tiempo Real
1. En tu servicio de Render, ve a la pestaña **"Logs"**
2. Puedes ver logs en tiempo real
3. Útil para debugging y monitoreo

### Métricas
- Render proporciona métricas básicas de uso
- Puedes ver requests, errores y tiempo de respuesta
- Útil para monitorear el rendimiento

## 🔄 Actualizaciones

Para actualizar tu API:

1. Haz cambios en tu repositorio fork
2. Push a GitHub
3. Render detectará automáticamente los cambios
4. Reconstruirá y redesplegará automáticamente

## 💰 Costos

- **Plan Gratuito:** Incluye:
  - 750 horas de ejecución por mes
  - 512MB RAM
  - 1 vCPU
  - 10GB de almacenamiento
  - Sleep automático después de 15 minutos de inactividad

- **Plan Pago:** Desde $7/mes para:
  - Ejecución continua (sin sleep)
  - Más recursos
  - Soporte prioritario

## 🎯 Próximos Pasos

Una vez desplegada tu API:

1. **Prueba los endpoints** con herramientas como Postman o curl
2. **Integra con tu aplicación** usando la URL de Render
3. **Monitorea el rendimiento** usando los logs de Render
4. **Configura alertas** si es necesario

## 📚 Recursos Adicionales

- [Documentación oficial de Render](https://render.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [GitHub del proyecto](https://github.com/tu-usuario/api-market-publico)

---

**¡Felicidades! 🎉 Tu HB API está ahora desplegada en Render y es completamente pública.**
