# Guía de Comandos - Terminal UBTool

## ℹ️ Información Importante

La terminal de UBTool te da acceso **directo al shell del dispositivo Ubuntu Touch**, no a ADB. 
Ya estás dentro del dispositivo, así que ejecuta comandos del sistema directamente.

## 📱 Comandos Básicos del Sistema

### Navegación y Archivos
```bash
# Listar archivos
ls -la
ls ~/Documents

# Cambiar directorio
cd /home/phablet
cd ~/Documents
cd /etc

# Ver contenido de archivos
cat /etc/os-release
cat /proc/version

# Crear directorios
mkdir ~/Test
```

### Información del Sistema
```bash
# Información del dispositivo
getprop ro.product.model
getprop ro.build.version.release

# Información de la batería
upower -i $(upower -e | grep battery)

# Espacio en disco
df -h

# Memoria
free -h

# Procesos
ps aux
top
htop
```

### Red
```bash
# Interfaces de red
ip addr
ifconfig

# Conexiones activas
netstat -tuln

# Ping
ping google.com
```

## 🚀 Comandos Ubuntu Touch Específicos

### Gestión de Aplicaciones
```bash
# Listar aplicaciones instaladas
click list

# Información de una aplicación
click info com.ubuntu.camera

# Ver logs de aplicaciones
journalctl -f -u unity8
```

### Sistema Lubuntu/Unity8
```bash
# Ver servicios
systemctl list-units

# Reiniciar UI
systemctl restart unity8

# Ver configuración
settings list
```

### Content Hub (Gestión de Contenido)
```bash
# Ver tipos de contenido
content-query

# Ver música
content-query music

# Ver documentos
content-query documents
```

## 🔧 Comandos de Desarrollo

### Logs y Debugging
```bash
# Logs del sistema
journalctl -f

# Logs de ADB (si necesitas)
logcat

# Mensajes del kernel
dmesg | tail
```

### Gestión de Paquetes
```bash
# Actualizar paquetes
sudo apt update
sudo apt upgrade

# Buscar paquetes
apt search python

# Instalar paquetes
sudo apt install htop
```

## ⚠️ Comandos que NO funcionan (y por qué)

Estos comandos ADB no funcionan porque ya estás dentro del shell:

```bash
# ❌ NO FUNCIONAN
adb shell          # Ya estás en shell
adb devices        # Comando ADB, no del dispositivo
adb reboot         # Comando ADB, no del dispositivo
adb push/pull      # Comandos ADB, no del dispositivo
```

## ✅ Alternativas correctas

En lugar de `adb reboot`:
```bash
# ✅ COMANDO CORRECTO
reboot
sudo reboot
```

En lugar de `adb push/pull`:
```bash
# ✅ Usa la web o SCP
# Para transferencia de archivos, usa otras herramientas
```

## 🎯 Ejemplos Prácticos

### 1. Ver información del dispositivo
```bash
getprop | grep -E "(model|version|brand)"
cat /etc/os-release
uname -a
```

### 2. Ver procesos y memoria
```bash
ps aux | grep unity8
free -h
df -h
```

### 3. Navegar por archivos
```bash
cd ~/Documents
ls -la
cd /home/phablet
find . -name "*.conf" | head -10
```

### 4. Ver logs en tiempo real
```bash
journalctl -f
tail -f /var/log/syslog
```

## 📋 Tips Útiles

1. **Autocompletar**: Usa `Tab` para autocompletar comandos y rutas
2. **Historial**: Usa flechas ↑/↓ para ver comandos anteriores
3. **Ayuda**: `man <comando>` para ver el manual de un comando
4. **Salir**: `exit` para cerrar la sesión (pero la terminal web permanecerá activa)

## 🔐 Permisos

Algunos comandos requieren `sudo`:
```bash
sudo reboot
sudo apt update
sudo systemctl restart unity8
```

La terminal te da control completo sobre tu dispositivo Ubuntu Touch. ¡Úsala responsablemente!
