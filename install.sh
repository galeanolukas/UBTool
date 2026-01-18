#!/bin/bash

# UBTool Installer for Linux
# Web app autoinstalable para Ubuntu Touch ADB Connection

echo "🚀 Instalando UBTool - Ubuntu Touch Connection Tool"

# Verificar si Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado. Por favor instálalo primero."
    exit 1
fi

# Verificar si pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 no está instalado. Por favor instálalo primero."
    exit 1
fi

# Crear entorno virtual
echo "📦 Creando entorno virtual..."
python3 -m venv ubtool_env

# Activar entorno virtual e instalar dependencias
echo "🔧 Activando entorno virtual..."
source ubtool_env/bin/activate

# Instalar dependencias
echo "📚 Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt

# Verificar instalación de ADB
if ! command -v adb &> /dev/null; then
    echo "⚠️  ADB no está instalado. Instalando Android Debug Bridge..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update
        sudo apt-get install -y android-tools-adb
    elif command -v yum &> /dev/null; then
        sudo yum install -y android-tools
    elif command -v dnf &> /dev/null; then
        sudo dnf install -y android-tools
    else
        echo "❌ No se puede instalar ADB automáticamente. Por favor instálalo manualmente."
    fi
fi

# Crear script de inicio
echo "🎯 Creando script de inicio..."
cat > start_ubtool.sh << 'EOF'
#!/bin/bash
cd "$(dirname "$0")"
source ubtool_env/bin/activate
python app.py
EOF

chmod +x start_ubtool.sh

echo "✅ Instalación completada!"
echo ""
echo "🎉 Para iniciar UBTool:"
echo "   ./start_ubtool.sh"
echo ""
echo "🌐 La aplicación estará disponible en: http://localhost:8080"
echo "📱 Asegúrate de tener tu dispositivo Ubuntu Touch conectado vía USB"
