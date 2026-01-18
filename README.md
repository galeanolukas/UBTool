# UBTool - Ubuntu Touch Connection Tool

> Para aquellos que tienen la suerte de tener un dispositivo con Ubuntu Touch

Una herramienta web autoinstalable para conectar y gestionar dispositivos Ubuntu Touch vía ADB, diseñada con la pasión y los colores característicos de nuestra comunidad.

## ¿Por qué UBTool?

Si eres uno de los afortunados usuarios de Ubuntu Touch, sabes lo especial que es este sistema operativo móvil basado en Linux. UBTool nace de la necesidad de tener una interfaz moderna y accesible para gestionar nuestros dispositivos directamente desde el navegador, sin complicaciones técnicas.

## Características

- Interfaz web moderna con los colores icónicos de Ubuntu Touch (naranja y negro)
- Conexión ADB directa con tus dispositivos Ubuntu Touch
- Gestión múltiple de dispositivos conectados simultáneamente
- Terminal integrada con acceso real al shell del dispositivo
- Información detallada del sistema: batería, almacenamiento, red y más
- Autoinstalable en Linux y Windows con un solo comando
- Diseño responsive que se adapta a cualquier pantalla
- Tiempo real con actualización automática del estado

## Inspirado en Ubuntu Touch

Cada línea de código de UBTool está pensada para reflejar la filosofía de Ubuntu Touch:

- Colores: El naranja vibrante (#E95420) y el negro elegante (#312D2A)
- Simplicidad: Interfaz limpia y funcional sin complicaciones
- Libertad: Código abierto para que la comunidad pueda mejorarlo
- Comunidad: Desarrollado con ❤️ para los apasionados de Ubuntu Touch

## Instalación Rápida

### Para usuarios Linux

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/UBTool.git
cd UBTool

# Ejecutar el instalador mágico
./install.sh

# Iniciar tu herramienta
./start_ubtool.sh
```

### Para usuarios Windows

```cmd
# Clonar el repositorio
git clone https://github.com/tu-usuario/UBTool.git
cd UBTool

# Ejecutar el instalador
install.bat

# Iniciar la aplicación
start_ubtool.bat
```

### ¿Qué hace el instalador?

1. Crea un entorno virtual Python aislado y seguro
2. Instala todas las dependencias necesarias (Microdot, Jinja2, etc.)
3. Verifica ADB y lo instala si es necesario
4. Crea scripts de inicio para futuros usos
5. Configura todo para que funcione out-of-the-box

## Empezando a Usar UBTool

1. Conecta tu dispositivo Ubuntu Touch vía USB
2. Habilita depuración USB en:
   - Configuración del sistema → Sobre → Modo desarrollador
   - Activa "Depuración Android"
3. Abre tu navegador en `http://localhost:8080`
4. Disfruta de la interfaz web que detectará automáticamente tu dispositivo

## Terminal Shell - El Corazón de UBTool

Una de las características más poderosas es la terminal integrada que te da acceso **directo al shell de tu dispositivo Ubuntu Touch**:

### Comandos que te encantarán:

```bash
# Explora tu dispositivo
ls -la ~/Documents
cd /home/phablet/Pictures

# Información del sistema
getprop ro.product.model
cat /etc/os-release

# Gestión de procesos
ps aux | grep unity8
top

# Red y conectividad
ip addr
ping google.com

# Espacio y recursos
df -h
free -h
upower -i $(upower -e | grep battery)
```

### Comandos Ubuntu Touch especiales:

```bash
# Apps de Ubuntu Touch
click list
click info com.ubuntu.camera

# Sistema Unity8
systemctl status unity8
settings list

# Content Hub
content-query music
content-query documents

# Logs del sistema
journalctl -f -u unity8
```

> **Nota**: Ya estás dentro del shell del dispositivo, no necesitas `adb shell`. Simplemente escribe los comandos directamente.

## Estructura del Proyecto

```
UBTool/
├── app.py                 # Servidor principal con Microdot
├── requirements.txt       # Dependencias Python
├── install.sh            # Instalador mágico Linux
├── install.bat           # Instalador Windows
├── start_ubtool.sh       # Inicio rápido Linux
├── start_ubtool.bat      # Inicio rápido Windows
├── templates/
│   └── home.html         # Interfaz web principal
├── static/
│   ├── logo.png          # Logo Ubuntu Touch
│   ├── css/
│   │   └── ubtool.css    # Estilos personalizados
│   └── js/
│       └── ubtool.js     # JavaScript frontend
├── terminal_manager.py   # Gestor de terminales avanzado
├── commands_guide.md     # Guía completa de comandos
├── .gitignore           # Archivos ignorados por Git
└── README.md             # Este archivo de amor
```

## API Endpoints

Para desarrolladores que quieran extender UBTool:

- `GET /` - Página principal con toda la magia
- `GET /api/device/status` - Estado de conexión de dispositivos
- `GET /api/device/info` - Información detallada del dispositivo
- `POST /api/device/shell` - Ejecutar comandos shell
- `POST /api/device/reboot` - Reiniciar dispositivo
- `GET /api/adb/status` - Estado del servicio ADB

### Terminal API (Tiempo Real):

- `POST /api/terminal/create` - Crear sesión terminal
- `POST /api/terminal/<id>/write` - Enviar comandos
- `GET /api/terminal/<id>/output` - Obtener salida
- `POST /api/terminal/<id>/resize` - Redimensionar terminal
- `POST /api/terminal/<id>/close` - Cerrar sesión

## Tecnologías que Hacen la Magia

- **Backend**: Python con Microdot (ligero y potente)
- **Frontend**: HTML5, JavaScript moderno, W3.CSS
- **Terminal**: PTY Process para terminales reales
- **Temas**: Los colores que nos identifican como comunidad
- **Plantillas**: Jinja2 para renderizado eficiente

## Requisitos del Sistema

- **Python 3.7+** - El corazón del backend
- **ADB (Android Debug Bridge)** - El puente hacia tu dispositivo
- **Navegador moderno** - Chrome, Firefox, Safari, Edge
- **Dispositivo Ubuntu Touch** - La joya de la corona

## Colores de Nuestra Comunidad

- **Naranja Ubuntu**: `#E95420` - El color de la pasión
- **Negro elegante**: `#312D2A` - La seriedad del código
- **Blanco puro**: `#FFFFFF` - La claridad del diseño
- **Gris sutil**: `#AEA79F` - El equilibrio perfecto

## Contribuir a UBTool

¡Este es un proyecto comunitario! Si quieres contribuir:

1. **Haz un fork** del repositorio
2. **Crea una rama** con tu mejora: `git checkout -b feature/nueva-funcion`
3. **Haz commit** de tus cambios: `git commit -m 'Agregar nueva función mágica'`
4. **Push** a tu rama: `git push origin feature/nueva-funcion`
5. **Abre un Pull Request** y comparte tu magia

### Ideas para contribuir:

- Mejorar el diseño responsive
- Agregar notificaciones de sonido
- Gráficos de uso del dispositivo
- Soporte para múltiples idiomas
- Modo oscuro/claro
- Autenticación y seguridad

## Problemas Comunes y Soluciones

### "No se detecta mi dispositivo"
```bash
# Verificar conexión ADB
adb devices

# Si no aparece, revisa:
# 1. Depuración USB activada
# 2. Cable USB funcional
# 3. Confiar en el equipo desde el dispositivo
```

### "Error al instalar dependencias"
```bash
# Actualizar pip primero
pip install --upgrade pip

# Reinstalar entorno virtual
rm -rf ubtool_env
./install.sh
```

### "La terminal no responde"
- Asegúrate que el dispositivo esté conectado
- Reinicia la sesión terminal (cierra y abre la ventana)
- Verifica que ADB esté funcionando: `adb shell`

## Licencia

MIT License - Comparte, modifica y mejora libremente.

## Comunidad y Soporte

- **Issues**: Reporta problemas y sugerencias en GitHub
- **Discusiones**: Comparte ideas y experiencias
- **Wiki**: Documentación colaborativa
- **Telegram**: Únete a la comunidad Ubuntu Touch

## Agradecimientos

A toda la comunidad **Ubuntu Touch** por mantener vivo el sueño de un móvil libre y abierto. A los desarrolladores que dedican su tiempo a construir un mejor ecosistema. A los usuarios que confían en software libre.

---

> **"Soy porque somos"** - UBTool es posible gracias a una comunidad apasionada

**Desarrollado con ❤️ para la comunidad Ubuntu Touch**

---

*[Ubuntu Touch](https://ubuntu-touch.io/) • [UBPorts](https://ubports.com/) • [Comunidad](https://forums.ubports.com/)*
