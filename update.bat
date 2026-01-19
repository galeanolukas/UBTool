@echo off
setlocal enabledelayedexpansion

REM UBTool Updater Script for Windows
REM Version 1.0

title UBTool Updater

echo ==================================
echo     UBTool Updater v1.0
echo ==================================
echo.

REM Check if git is installed
echo [INFO] Verificando dependencias...
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git no está instalado. Por favor instala Git primero.
    pause
    exit /b 1
)

where curl >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Curl no está instalado. Por favor instala Curl primero.
    pause
    exit /b 1
)

echo [SUCCESS] Dependencias verificadas

REM Get current version
set CURRENT_VERSION=unknown
if exist version.txt (
    set /p CURRENT_VERSION=<version.txt
)

echo [INFO] Versión actual: %CURRENT_VERSION%

REM Get latest release version from GitHub
echo [INFO] Verificando última versión disponible...

REM Create temporary file for version info
curl -s "https://api.github.com/repos/lukasgaleano/UBTool/releases/latest" > temp_version.json

REM Parse version from JSON (simplified parsing)
findstr /C:"tag_name" temp_version.json > temp_tag.txt
for /f "tokens=2 delims=" %%a in (temp_tag.txt) do (
    set LATEST_VERSION=%%a
)

del temp_version.json temp_tag.txt

if "%LATEST_VERSION%"=="" (
    echo [ERROR] No se pudo obtener la última versión
    pause
    exit /b 1
)

echo [INFO] Última versión disponible: %LATEST_VERSION%

REM Compare versions
if "%CURRENT_VERSION%"=="%LATEST_VERSION%" (
    echo [SUCCESS] ¡Ya tienes la última versión (%LATEST_VERSION%)!
    pause
    exit /b 0
)

echo [WARNING] Hay una nueva versión disponible: %LATEST_VERSION%
set /p "¿Deseas actualizar? (y/N): " choice=
echo.

if /i not "%choice%"=="y" if /i not "%choice%"=="Y" (
    echo [INFO] Actualización cancelada
    pause
    exit /b 0
)

REM Backup current installation
echo [INFO] Creando backup de la instalación actual...

set BACKUP_DIR=backup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
mkdir "%BACKUP_DIR%" 2>nul

REM Backup important files
if exist templates (
    xcopy /E /I /Y templates "%BACKUP_DIR%\" >nul 2>&1
)
if exist static (
    xcopy /E /I /Y static "%BACKUP_DIR%\" >nul 2>&1
)
if exist app.py (
    copy app.py "%BACKUP_DIR%\" >nul 2>&1
)
if exist start_ubtool.sh (
    copy start_ubtool.sh "%BACKUP_DIR%\" >nul 2>&1
)
if exist requirements.txt (
    copy requirements.txt "%BACKUP_DIR%\" >nul 2>&1
)

echo [SUCCESS] Backup creado en: %BACKUP_DIR%

REM Download latest release
echo [INFO] Descargando UBTool v%LATEST_VERSION%...

REM Create temp directory
set TEMP_DIR=temp_update_%random%
mkdir "%TEMP_DIR%"

REM Download release
set DOWNLOAD_URL=https://github.com/lukasgaleano/UBTool/archive/refs/tags/v%LATEST_VERSION%.tar.gz
curl -L -o "%TEMP_DIR%\ubtool.tar.gz" "%DOWNLOAD_URL%"

if %errorlevel% neq 0 (
    echo [ERROR] Error al descargar la actualización
    rmdir /S /Q "%TEMP_DIR%"
    pause
    exit /b 1
)

echo [SUCCESS] Descarga completada

REM Extract and install
echo [INFO] Extrayendo archivos...

cd "%TEMP_DIR%"

REM Extract using tar (if available) or fallback to 7zip
tar -xzf ubtool.tar.gz >nul 2>&1
if %errorlevel% neq 0 (
    REM Try with 7zip if tar fails
    7z x ubtool.tar.gz >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Error al extraer archivos. Asegúrate de tener tar o 7zip instalado.
        cd ..
        rmdir /S /Q "%TEMP_DIR%"
        pause
        exit /b 1
    )
)

if %errorlevel% neq 0 (
    echo [ERROR] Error al extraer archivos
    cd ..
    rmdir /S /Q "%TEMP_DIR%"
    pause
    exit /b 1
)

echo [SUCCESS] Archivos extraídos

REM Find extracted directory
for /d %%d in (UBTool-*) do (
    set EXTRACTED_DIR=%%d
    goto :found
)
:found

if "%EXTRACTED_DIR%"=="" (
    echo [ERROR] No se encontró el directorio extraído
    cd ..
    rmdir /S /Q "%TEMP_DIR%"
    pause
    exit /b 1
)

REM Update files
echo [INFO] Actualizando archivos...

cd "%EXTRACTED_DIR%"

REM Update files (overwrite existing)
xcopy /E /I /Y * ..\ >nul 2>&1

if %errorlevel% neq 0 (
    echo [ERROR] Error al actualizar archivos
    cd ..\
    rmdir /S /Q "%TEMP_DIR%"
    pause
    exit /b 1
)

cd ..\
echo [SUCCESS] Archivos actualizados

REM Cleanup
echo [INFO] Limpiando archivos temporales...
rmdir /S /Q "%TEMP_DIR%"
echo [SUCCESS] Limpieza completada

REM Update version file
echo %LATEST_VERSION% > version.txt
echo [SUCCESS] Versión actualizada a v%LATEST_VERSION%

echo.
echo [SUCCESS] ¡UBTool ha sido actualizado exitosamente a v%LATEST_VERSION%!
echo [INFO] Por favor reinicia la aplicación para aplicar los cambios.
echo.
echo [INFO] Si encuentras algún problema, puedes restaurar desde el backup creado.
pause
