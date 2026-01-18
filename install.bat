@echo off
REM UBTool Installer for Windows
REM Web app autoinstalable para Ubuntu Touch ADB Connection

echo 🚀 Instalando UBTool - Ubuntu Touch Connection Tool
echo.

REM Verificar si Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python no está instalado. Por favor instálalo desde https://python.org
    pause
    exit /b 1
)

REM Verificar si pip está instalado
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ pip no está instalado. Por favor instálalo primero.
    pause
    exit /b 1
)

REM Crear entorno virtual
echo 📦 Creando entorno virtual...
python -m venv ubtool_env

REM Activar entorno virtual e instalar dependencias
echo 🔧 Activando entorno virtual...
call ubtool_env\Scripts\activate.bat

REM Instalar dependencias
echo 📚 Instalando dependencias...
python -m pip install --upgrade pip
pip install -r requirements.txt

REM Verificar instalación de ADB
adb version >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  ADB no está instalado o no está en el PATH
    echo Por favor descarga e instala Android SDK Platform Tools desde:
    echo https://developer.android.com/studio/releases/platform-tools
    echo Y añade la carpeta platform-tools a tu PATH del sistema
    echo.
)

REM Crear script de inicio
echo 🎯 Creando script de inicio...
echo @echo off > start_ubtool.bat
echo cd /d "%%~dp0" >> start_ubtool.bat
echo call ubtool_env\Scripts\activate.bat >> start_ubtool.bat
echo python app.py >> start_ubtool.bat

echo.
echo ✅ Instalación completada!
echo.
echo 🎉 Para iniciar UBTool:
echo    start_ubtool.bat
echo.
echo 🌐 La aplicación estará disponible en: http://localhost:8080
echo 📱 Asegúrate de tener tu dispositivo Ubuntu Touch conectado vía USB
echo.
pause
