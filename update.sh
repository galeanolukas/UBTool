#!/bin/bash

# UBTool Updater Script for Linux/macOS
# Version 1.0

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if git is installed
check_dependencies() {
    print_info "Verificando dependencias..."
    
    if ! command -v git &> /dev/null; then
        print_error "Git no está instalado. Por favor instala Git primero."
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        print_error "Curl no está instalado. Por favor instala Curl primero."
        exit 1
    fi
    
    print_success "Dependencias verificadas"
}

# Get current version
get_current_version() {
    if [ -f "version.txt" ]; then
        CURRENT_VERSION=$(cat version.txt)
    else
        CURRENT_VERSION="unknown"
    fi
    print_info "Versión actual: $CURRENT_VERSION"
}

# Get latest release version from GitHub
get_latest_version() {
    print_info "Verificando última versión disponible..."
    
    LATEST_VERSION=$(curl -s "https://api.github.com/repos/lukasgaleano/UBTool/releases/latest" | grep -o '"tag_name": "[^"]*' | sed -E 's/.*"([^"]*)".*/\1/')
    
    if [ -z "$LATEST_VERSION" ]; then
        print_error "No se pudo obtener la última versión"
        exit 1
    fi
    
    print_info "Última versión disponible: $LATEST_VERSION"
}

# Compare versions
compare_versions() {
    if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
        print_success "¡Ya tienes la última versión ($LATEST_VERSION)!"
        exit 0
    fi
    
    print_warning "Hay una nueva versión disponible: $LATEST_VERSION"
    read -p "¿Deseas actualizar? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_info "Actualización cancelada"
        exit 0
    fi
}

# Backup current installation
backup_current() {
    print_info "Creando backup de la instalación actual..."
    
    BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # Backup important files
    cp -r templates "$BACKUP_DIR/" 2>/dev/null || true
    cp -r static "$BACKUP_DIR/" 2>/dev/null || true
    cp app.py "$BACKUP_DIR/" 2>/dev/null || true
    cp start_ubtool.sh "$BACKUP_DIR/" 2>/dev/null || true
    cp requirements.txt "$BACKUP_DIR/" 2>/dev/null || true
    
    print_success "Backup creado en: $BACKUP_DIR"
}

# Download latest release
download_latest() {
    print_info "Descargando UBTool v$LATEST_VERSION..."
    
    # Create temp directory
    TEMP_DIR="temp_update_$$"
    mkdir -p "$TEMP_DIR"
    
    # Download release
    DOWNLOAD_URL="https://github.com/lukasgaleano/UBTool/archive/refs/tags/v$LATEST_VERSION.tar.gz"
    curl -L -o "$TEMP_DIR/ubtool.tar.gz" "$DOWNLOAD_URL"
    
    if [ $? -ne 0 ]; then
        print_error "Error al descargar la actualización"
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    print_success "Descarga completada"
}

# Extract and install
extract_install() {
    print_info "Extrayendo archivos..."
    
    # Extract
    cd "$TEMP_DIR"
    tar -xzf ubtool.tar.gz
    
    if [ $? -ne 0 ]; then
        print_error "Error al extraer archivos"
        cd ..
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    # Find extracted directory
    EXTRACTED_DIR=$(ls -d UBTool-* 2>/dev/null | head -1)
    
    if [ -z "$EXTRACTED_DIR" ]; then
        print_error "No se encontró el directorio extraído"
        cd ..
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    print_success "Archivos extraídos"
}

# Update files
update_files() {
    print_info "Actualizando archivos..."
    
    cd "$EXTRACTED_DIR"
    
    # Update files (overwrite existing)
    cp -r * ../.. 2>/dev/null
    
    if [ $? -ne 0 ]; then
        print_error "Error al actualizar archivos"
        cd ../..
        rm -rf "$TEMP_DIR"
        exit 1
    fi
    
    cd ../..
    print_success "Archivos actualizados"
}

# Cleanup
cleanup() {
    print_info "Limpiando archivos temporales..."
    rm -rf "$TEMP_DIR"
    print_success "Limpieza completada"
}

# Update version file
update_version() {
    echo "$LATEST_VERSION" > version.txt
    print_success "Versión actualizada a v$LATEST_VERSION"
}

# Main update function
main() {
    echo "=================================="
    echo "    UBTool Updater v1.0"
    echo "=================================="
    echo
    
    check_dependencies
    get_current_version
    get_latest_version
    compare_versions
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        backup_current
        download_latest
        extract_install
        update_files
        cleanup
        update_version
        
        echo
        print_success "¡UBTool ha sido actualizado exitosamente a v$LATEST_VERSION!"
        print_info "Por favor reinicia la aplicación para aplicar los cambios."
        echo
        print_info "Si encuentras algún problema, puedes restaurar desde el backup creado."
    fi
}

# Run main function
main "$@"
