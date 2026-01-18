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
echo echo 🚀 Iniciando UBTool - Ubuntu Touch Connection Tool >> start_ubtool.bat
echo echo 🌐 Iniciando servidor web... >> start_ubtool.bat
echo start /B python app.py >> start_ubtool.bat
echo timeout /t 3 /nobreak ^>nul >> start_ubtool.bat
echo echo 🌍 Abriendo navegador... >> start_ubtool.bat
echo start http://localhost:8080 >> start_ubtool.bat
echo echo ✅ UBTool iniciado correctamente >> start_ubtool.bat
echo echo 📱 Mantén esta ventana abierta para mantener UBTool funcionando >> start_ubtool.bat
echo pause >> start_ubtool.bat

REM Crear acceso directo en el escritorio
echo 🖥️ Creando acceso directo en el escritorio...

REM Obtener la ruta actual y del escritorio
set "CURRENT_DIR=%CD%"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\UBTool.lnk"

REM Crear script VBScript temporal para generar el acceso directo
echo Set oWS = WScript.CreateObject("WScript.Shell") > CreateShortcut.vbs
echo sLinkFile = "%SHORTCUT_PATH%" >> CreateShortcut.vbs
echo Set oLink = oWS.CreateShortcut(sLinkFile) >> CreateShortcut.vbs
echo oLink.TargetPath = "%CURRENT_DIR%\start_ubtool.bat" >> CreateShortcut.vbs
echo oLink.WorkingDirectory = "%CURRENT_DIR%" >> CreateShortcut.vbs
echo oLink.Description = "UBTool - Ubuntu Touch Connection Tool" >> CreateShortcut.vbs
echo oLink.IconLocation = "%CURRENT_DIR%\static\logo.png, 0" >> CreateShortcut.vbs
echo oLink.Save >> CreateShortcut.vbs

REM Ejecutar el script VBScript
cscript //nologo CreateShortcut.vbs

REM Limpiar script temporal
del CreateShortcut.vbs

echo.
echo ✅ Instalación completada!
echo.
echo 🎉 Para iniciar UBTool:
echo    • Doble clic en el acceso directo "UBTool" en tu escritorio
echo    • O ejecuta: start_ubtool.bat
echo.
echo 🌐 La aplicación se abrirá automáticamente en: http://localhost:8080
echo 📱 Asegúrate de tener tu dispositivo Ubuntu Touch conectado vía USB
echo.
echo 💡 El acceso directo en el escritorio iniciará UBTool y abrirá tu navegador automáticamente
echo.
pause
