# 🖥️ Despliegue en VPS con Docker - HB API

Guía completa para desplegar la HB API en un VPS usando Docker y Docker Compose.

## 📋 Prerrequisitos

- ✅ VPS con Ubuntu 20.04+ o similar
- ✅ Acceso SSH al VPS
- ✅ Credenciales de HomeBroker (DNI, usuario, contraseña)
- ✅ Dominio (opcional, para HTTPS)

## 🖥️ Requisitos del VPS

### Especificaciones Mínimas
- **Sistema Operativo:** Ubuntu 20.04 LTS o superior
- **RAM:** 1GB mínimo (recomendado 2GB+)
- **CPU:** 1 vCPU mínimo
- **Almacenamiento:** 10GB mínimo
- **Red:** Conexión a internet estable

### Especificaciones Recomendadas
- **RAM:** 2GB o más
- **CPU:** 2 vCPU o más
- **Almacenamiento:** 20GB SSD
- **Red:** Banda ancha estable

## 🔧 Instalación Paso a Paso

### 1. Conectar al VPS

```bash
ssh usuario@tu-vps-ip
```

**Reemplaza:**
- `usuario` con tu nombre de usuario del VPS
- `tu-vps-ip` con la IP de tu VPS

### 2. Actualizar el Sistema

```bash
# Actualizar lista de paquetes
sudo apt update

# Actualizar paquetes instalados
sudo apt upgrade -y

# Instalar herramientas básicas
sudo apt install -y curl wget git nano htop
```

### 3. Instalar Docker

```bash
# Descargar script de instalación de Docker
curl -fsSL https://get.docker.com -o get-docker.sh

# Ejecutar script de instalación
sudo sh get-docker.sh

# Agregar usuario actual al grupo docker
sudo usermod -aG docker $USER

# Verificar instalación
docker --version
```

### 4. Instalar Docker Compose

```bash
# Descargar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Dar permisos de ejecución
sudo chmod +x /usr/local/bin/docker-compose

# Verificar instalación
docker-compose --version
```

### 5. Reiniciar Sesión

```bash
# Salir del VPS
exit

# Reconectar para aplicar cambios de grupo
ssh usuario@tu-vps-ip

# Verificar que Docker funcione sin sudo
docker ps
```

### 6. Clonar el Repositorio

```bash
# Clonar repositorio
git clone https://github.com/tu-usuario/api-market-publico.git

# Entrar al directorio
cd api-market-publico

# Verificar archivos
ls -la
```

### 7. Configurar Variables de Entorno

```bash
# Copiar archivo de ejemplo
cp env.example .env

# Editar archivo de configuración
nano .env
```

**Contenido del archivo `.env`:**
```bash
# Configuración de HomeBroker (OBLIGATORIAS)
HB_BROKER=0
HB_DNI=tu_dni_real_aqui
HB_USER=tu_usuario_real_aqui
HB_PASSWORD=tu_password_real_aqui

# Prefijos de opciones (opcional)
HB_OPTIONS_PREFIXES=GFG,GAL

# Prefijos de acciones (opcional)
HB_STOCK_PREFIXES=GGAL,YPFD,PAMP

# Archivo de configuración de tickers
HB_TICKERS_FILE=tickers.json

# Configuración de reconexión automática
HB_RECONNECT_INTERVAL=30
HB_MAX_RECONNECT_ATTEMPTS=5
HB_HEALTH_CHECK_INTERVAL=60
```

**⚠️ IMPORTANTE:** 
- Cambia `tu_dni_real_aqui`, `tu_usuario_real_aqui` y `tu_password_real_aqui` por tus credenciales reales
- **NUNCA** subas este archivo `.env` a GitHub

### 8. Configurar Firewall (Opcional pero Recomendado)

```bash
# Instalar UFW si no está instalado
sudo apt install ufw -y

# Configurar reglas básicas
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Permitir SSH
sudo ufw allow ssh

# Permitir puerto de la API
sudo ufw allow 8080

# Habilitar firewall
sudo ufw enable

# Verificar estado
sudo ufw status
```

### 9. Levantar la Aplicación

```bash
# Construir y levantar contenedores
docker-compose up -d

# Verificar que estén corriendo
docker-compose ps

# Ver logs en tiempo real
docker-compose logs -f
```

### 10. Verificar Funcionamiento

```bash
# Probar endpoint de salud
curl http://localhost:8080/health

# Probar endpoint principal
curl http://localhost:8080/

# Ver logs del contenedor
docker-compose logs hb-api
```

## 🔍 Monitoreo y Mantenimiento

### Ver Logs en Tiempo Real

```bash
# Ver todos los logs
docker-compose logs -f

# Ver logs de un servicio específico
docker-compose logs -f hb-api

# Ver últimos 100 logs
docker-compose logs --tail=100 hb-api
```

### Verificar Estado de Contenedores

```bash
# Estado de contenedores
docker-compose ps

# Estadísticas de uso
docker stats

# Espacio en disco
df -h
```

### Reiniciar Servicios

```bash
# Reiniciar todos los servicios
docker-compose restart

# Reiniciar solo la API
docker-compose restart hb-api

# Parar y levantar de nuevo
docker-compose down
docker-compose up -d
```

## 🔒 Configuración de Seguridad

### 1. Usuario No-Root

El Dockerfile ya está configurado para ejecutar como usuario no-root.

### 2. Firewall

```bash
# Verificar reglas del firewall
sudo ufw status verbose

# Agregar reglas adicionales si es necesario
sudo ufw allow from tu-ip-especifica to any port 8080
```

### 3. Monitoreo de Logs

```bash
# Crear directorio para logs
mkdir -p logs

# Ver logs de acceso
tail -f logs/access.log

# Ver logs de errores
tail -f logs/error.log
```

## 🌐 Configuración de Dominio (Opcional)

### 1. Configurar DNS

```bash
# Agregar registro A en tu proveedor de DNS
# A tu-dominio.com -> IP-DE-TU-VPS
```

### 2. Configurar Nginx como Proxy Inverso

```bash
# Instalar Nginx
sudo apt install nginx -y

# Crear configuración
sudo nano /etc/nginx/sites-available/hb-api
```

**Contenido de la configuración:**
```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Habilitar sitio
sudo ln -s /etc/nginx/sites-available/hb-api /etc/nginx/sites-enabled/

# Verificar configuración
sudo nginx -t

# Recargar Nginx
sudo systemctl reload nginx

# Permitir puerto 80 en firewall
sudo ufw allow 80
```

### 3. Configurar HTTPS con Let's Encrypt

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtener certificado
sudo certbot --nginx -d tu-dominio.com

# Verificar renovación automática
sudo certbot renew --dry-run
```

## 🔄 Actualizaciones

### Actualizar Código

```bash
# Entrar al directorio
cd api-market-publico

# Obtener cambios más recientes
git pull origin main

# Reconstruir y levantar
docker-compose down
docker-compose up -d --build
```

### Actualizar Docker

```bash
# Actualizar Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Actualizar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## 🚨 Solución de Problemas

### Error de Conexión

```bash
# Verificar estado de contenedores
docker-compose ps

# Ver logs de error
docker-compose logs hb-api

# Verificar variables de entorno
docker-compose exec hb-api env | grep HB_
```

### Error de Memoria

```bash
# Ver uso de memoria
free -h

# Ver uso de swap
swapon --show

# Si es necesario, crear swap
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Error de Disco

```bash
# Ver uso de disco
df -h

# Limpiar imágenes Docker no utilizadas
docker system prune -a

# Limpiar logs
sudo journalctl --vacuum-time=7d
```

## 📊 Monitoreo Avanzado

### 1. Monitoreo de Recursos

```bash
# Instalar herramientas de monitoreo
sudo apt install htop iotop nethogs -y

# Monitorear en tiempo real
htop
```

### 2. Logs Estructurados

```bash
# Ver logs con timestamps
docker-compose logs -t hb-api

# Filtrar logs por fecha
docker-compose logs --since="2024-01-01" hb-api
```

### 3. Backup de Configuración

```bash
# Crear backup del archivo .env
cp .env .env.backup.$(date +%Y%m%d)

# Crear backup de la configuración completa
tar -czf backup-$(date +%Y%m%d).tar.gz .env tickers.json
```

## 🎯 Próximos Pasos

Una vez desplegada tu API en VPS:

1. **Configura monitoreo** con herramientas como Prometheus + Grafana
2. **Implementa backup automático** de la configuración
3. **Configura alertas** para problemas de conexión
4. **Optimiza rendimiento** según el uso
5. **Considera balanceador de carga** si tienes mucho tráfico

## 📚 Recursos Adicionales

- [Documentación oficial de Docker](https://docs.docker.com/)
- [Documentación de Docker Compose](https://docs.docker.com/compose/)
- [Guía de Ubuntu Server](https://ubuntu.com/server)
- [Documentación de Nginx](https://nginx.org/en/docs/)

---

**¡Felicidades! 🎉 Tu HB API está ahora desplegada en VPS con Docker y es completamente pública.**
