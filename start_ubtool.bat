@echo off
REM UBTool Startup Script for Windows
REM Inicia el servidor y abre el navegador automáticamente

echo 🚀 Iniciando UBTool - Ubuntu Touch Connection Tool

REM Activar entorno virtual
call ubtool_env\Scripts\activate.bat

REM Iniciar servidor en segundo plano
echo 🌐 Iniciando servidor web...
start /B python app.py

REM Esperar un momento para que el servidor inicie
timeout /t 3 /nobreak >nul

REM Abrir navegador automáticamente
echo 🌍 Abriendo navegador...
start http://localhost:8080

echo ✅ UBTool iniciado correctamente
echo 📱 Abre tu navegador en: http://localhost:8080
echo 📱 Asegúrate de tener tu dispositivo Ubuntu Touch conectado vía USB
echo.
echo ⚠️  Mantén esta ventana abierta para mantener UBTool funcionando
echo    Cierra esta ventana para detener UBTool
echo.
pause
