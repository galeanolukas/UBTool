# UBTool - Ubuntu Touch Connection Tool

> Para aquellos que tienen la suerte de tener un dispositivo con Ubuntu Touch

Una herramienta web autoinstalable para conectar y gestionar dispositivos Ubuntu Touch vía ADB, diseñada con la pasión y los colores característicos de nuestra comunidad.

**Autor:** Lukas Galeano <galeanolukas@gmail.com>

## 🌟 Misión: Dar Vida a Ubuntu Touch

Este proyecto nace con una visión clara: **dar vida a Ubuntu Touch y ayudar a que este sistema operativo crezca y sea mantenido por nuestra comunidad**. 

Ubuntu Touch no es solo un sistema operativo móvil, es un sueño de libertad, un proyecto que demuestra que podemos tener alternativas reales y abiertas en el mundo móvil. Cada línea de código de UBTool está escrita con el propósito de:

- 🌱 **Hacer crecer** el ecosistema Ubuntu Touch
- 👥 **Fortalecer la comunidad** que lo mantiene vivo
- 🔧 **Facilitar el desarrollo** y la gestión de dispositivos
- 🚀 **Inspirar a más usuarios** a unirse a esta revolución

## ¿Por qué UBTool?

Si eres uno de los afortunados usuarios de Ubuntu Touch, sabes lo especial que es este sistema operativo móvil basado en Linux. UBTool nace de la necesidad de tener una interfaz moderna y accesible para gestionar nuestros dispositivos directamente desde el navegador, sin complicaciones técnicas.

**Nuestro objetivo es simple pero poderoso: que más personas puedan disfrutar, desarrollar y contribuir a Ubuntu Touch.**

## Características

- Interfaz web moderna con los colores icónicos de Ubuntu Touch (naranja y negro)
- Conexión ADB directa con tus dispositivos Ubuntu Touch
- Gestión múltiple de dispositivos conectados simultáneamente
- Terminal integrada con acceso real al shell del dispositivo
- Botón para elevar privilegios a **root** desde la terminal (vía `sudo`)
- Información detallada del sistema: batería, almacenamiento, red y más
- File Manager: navegación por carpetas del dispositivo
- Viewer/Editor: abre archivos de texto para editar y guarda cambios; previsualiza imágenes y reproduce videos desde el navegador
- Herramientas para crear **WebApps en Python** en el dispositivo (Microdot/Flask/FastAPI) con entorno virtual
- Abrir una URL en el **navegador por defecto del dispositivo** (ideal para probar WebApps)
- Autoinstalable en Linux y Windows con un solo comando
- Diseño responsive que se adapta a cualquier pantalla
- Tiempo real con actualización automática del estado
- Interfaz con **2 idiomas**: Español (por defecto) e Inglés (ES/EN)

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

# Ejecutar el instalador mágico
install.bat

# ¡Listo! Doble clic en el acceso directo "UBTool" en tu escritorio
# O ejecuta: start_ubtool.bat
```

### ¿Qué hace el instalador?

1. **Crea un entorno virtual** Python aislado y seguro
2. **Instala todas las dependencias** necesarias (Microdot, Jinja2, etc.)
3. **Verifica ADB** y lo instala si es necesario
4. **Crea scripts de inicio** para futuros usos
5. **Crea acceso directo** en el escritorio con icono Ubuntu Touch
6. **Configura todo** para que funcione out-of-the-box
7. **Inicia automáticamente** el navegador al ejecutar UBTool

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
- `POST /api/device/open_url` - Abrir una URL en el navegador por defecto del dispositivo
- `POST /api/device/reboot` - Reiniciar dispositivo
- `GET /api/adb/status` - Estado del servicio ADB

### File Manager API:

- `GET /api/files/list?path=/ruta` - Listar archivos y carpetas del dispositivo
- `GET /api/files/raw?path=/ruta/archivo` - Leer archivo binario (viewer/descarga)
- `GET /api/files/text?path=/ruta/archivo` - Leer archivo de texto (para editor)
- `POST /api/files/write` - Guardar archivo de texto en el dispositivo

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

## Apoya el proyecto

Si UBTool te resulta útil y quieres apoyar el desarrollo, puedes invitarme un café:

- https://buymeacoffee.com/lukasgaleano

## Agradecimientos

Este proyecto es un homenaje a toda la comunidad **Ubuntu Touch** que mantiene vivo el sueño de un móvil libre y abierto. 

A los desarrolladores de **UBPorts** que dedican su tiempo y conocimiento para construir un mejor ecosistema. A cada usuario que confía en el software libre y elige la libertad sobre la comodidad. A todos aquellos que creen que otro mundo móvil es posible.

**Ubuntu Touch es más que código, es un movimiento.** Es la prueba de que cuando una comunidad se une con propósito, puede crear algo verdaderamente revolucionario.

---

> **"Soy porque somos"** - UBTool es posible gracias a una comunidad que no se rinde

**Desarrollado con ❤️ por Lukas Galeano para la comunidad Ubuntu Touch**
**Contacto:** galeanolukas@gmail.com

**Visión:** Un futuro donde Ubuntu Touch no solo sobreviva, sino prospere y crezca gracias al esfuerzo colectivo de una comunidad apasionada.

---

*Este proyecto es mi contribución personal para dar vida a Ubuntu Touch y asegurar que este increíble sistema operativo móvil continúe creciendo y evolucionando con el apoyo de nuestra increíble comunidad.*

*[Ubuntu Touch](https://ubuntu-touch.io/) • [UBPorts](https://ubports.com/) • [Comunidad](https://forums.ubports.com/)*
