#!/usr/bin/env python3
"""
UBTool - Ubuntu Touch Connection Tool
Web app autoinstalable para conectar dispositivos Ubuntu Touch vía ADB

Autor: Lukas Galeano <galeanolukas@gmail.com>
Misión: Dar vida a Ubuntu Touch y ayudar a que el SO crezca y sea mantenido por la comunidad
"""

import os
import subprocess
import sys
import asyncio
import json
import uuid
from threading import Thread

from microdot import Microdot
from microdot.jinja import Template
from microdot.cors import CORS

# Import terminal manager
from terminal_manager import TerminalManager

app = Microdot()
CORS(app, allowed_origins="*", allow_credentials=True)

# Configuration
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 8080))

class ADBManager:
    """Maneja las operaciones de ADB"""
    
    def __init__(self):
        self.adb_path = self._find_adb()
    
    def _find_adb(self):
        """Busca el ejecutable de ADB en el sistema"""
        # Common ADB paths
        possible_paths = [
            'adb',
            '/usr/bin/adb',
            '/usr/local/bin/adb',
            'platform-tools/adb',
            'C:/Platform-tools/adb.exe',
            'C:/Android/Platform-tools/adb.exe'
        ]
        
        for path in possible_paths:
            try:
                result = subprocess.run([path, 'version'], 
                                      capture_output=True, 
                                      text=True, 
                                      timeout=5)
                if result.returncode == 0:
                    return path
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        return None
    
    def is_available(self):
        """Verifica si ADB está disponible"""
        return self.adb_path is not None
    
    def get_devices(self):
        """Obtiene la lista de dispositivos conectados"""
        if not self.is_available():
            return []
        
        try:
            result = subprocess.run([self.adb_path, 'devices'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=10)
            
            devices = []
            lines = result.stdout.strip().split('\n')[1:]  # Skip header
            
            for line in lines:
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        devices.append({
                            'id': parts[0],
                            'status': parts[1]
                        })
            
            return devices
        except subprocess.TimeoutExpired:
            return []
        except Exception as e:
            print(f"Error getting devices: {e}")
            return []
    
    def get_device_info(self, device_id=None):
        """Obtiene información detallada del dispositivo"""
        if not self.is_available():
            return None
        
        devices = self.get_devices()
        if not devices:
            return None
        
        # Use first device if none specified
        if not device_id:
            device_id = devices[0]['id']
        
        try:
            info = {}
            
            # Get device properties
            properties = [
                ('model', 'ro.product.model'),
                ('version', 'ro.build.version.release'),
                ('serial', 'ro.serialno'),
                ('manufacturer', 'ro.product.manufacturer'),
                ('brand', 'ro.product.brand')
            ]
            
            for key, prop in properties:
                try:
                    result = subprocess.run([
                        self.adb_path, '-s', device_id, 'shell', 'getprop', prop
                    ], capture_output=True, text=True, timeout=5)
                    
                    if result.returncode == 0:
                        info[key] = result.stdout.strip()
                    else:
                        info[key] = 'N/A'
                except subprocess.TimeoutExpired:
                    info[key] = 'Timeout'
            
            # Get battery info
            try:
                result = subprocess.run([
                    self.adb_path, '-s', device_id, 'shell', 
                    'dumpsys', 'battery'
                ], capture_output=True, text=True, timeout=10)
                
                if result.returncode == 0:
                    battery_info = self._parse_battery_info(result.stdout)
                    info['battery'] = battery_info
                else:
                    info['battery'] = 'N/A'
            except subprocess.TimeoutExpired:
                info['battery'] = 'Timeout'
            
            return info
            
        except Exception as e:
            print(f"Error getting device info: {e}")
            return None
    
    def _parse_battery_info(self, battery_output):
        """Parsea la información de la batería"""
        try:
            lines = battery_output.split('\n')
            for line in lines:
                if 'level:' in line:
                    level = line.split(':')[1].strip()
                    return f"{level}%"
            return 'N/A'
        except:
            return 'N/A'
    
    def execute_shell_command(self, command, device_id=None):
        """Ejecuta un comando shell en el dispositivo"""
        if not self.is_available():
            return {'error': 'ADB no disponible'}
        
        devices = self.get_devices()
        if not devices:
            return {'error': 'No hay dispositivos conectados'}
        
        # Use first device if none specified
        if not device_id:
            device_id = devices[0]['id']
        
        try:
            result = subprocess.run([
                self.adb_path, '-s', device_id, 'shell', command
            ], capture_output=True, text=True, timeout=30)
            
            return {
                'output': result.stdout,
                'error': result.stderr if result.returncode != 0 else None,
                'return_code': result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return {'error': 'Comando timeout'}
        except Exception as e:
            return {'error': str(e)}
    
    def reboot_device(self, device_id=None):
        """Reinicia el dispositivo"""
        if not self.is_available():
            return {'success': False, 'error': 'ADB no disponible'}
        
        devices = self.get_devices()
        if not devices:
            return {'success': False, 'error': 'No hay dispositivos conectados'}
        
        # Use first device if none specified
        if not device_id:
            device_id = devices[0]['id']
        
        try:
            result = subprocess.run([
                self.adb_path, '-s', device_id, 'reboot'
            ], capture_output=True, text=True, timeout=10)
            
            return {
                'success': result.returncode == 0,
                'error': result.stderr if result.returncode != 0 else None
            }
            
        except subprocess.TimeoutExpired:
            return {'success': False, 'error': 'Reinicio timeout'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Initialize ADB Manager and Terminal Manager
adb_manager = ADBManager()
terminal_manager = TerminalManager(adb_manager)

# Template rendering function
def render_template(template_name, **context):
    """Renderiza un template Jinja2"""
    template_path = os.path.join('templates', template_name)
    with open(template_path, 'r', encoding='utf-8') as f:
        template_content = f.read()
    
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.from_string(template_content)
    return template.render(**context)

# Routes
@app.route('/')
async def index(request):
    """Página principal"""
    from microdot import Response
    html_content = render_template('home.html')
    return Response(html_content, headers={'Content-Type': 'text/html; charset=utf-8'})

@app.route('/static/<path:path>')
async def static_files(request, path):
    """Sirve archivos estáticos"""
    from microdot import send_file
    return send_file(f'static/{path}')

# API Routes
@app.route('/api/device/status')
async def device_status(request):
    """API: Estado del dispositivo"""
    if not adb_manager.is_available():
        return {
            'connected': False,
            'error': 'ADB no disponible',
            'devices': []
        }
    
    devices = adb_manager.get_devices()
    
    if devices:
        return {
            'connected': True,
            'devices': devices,
            'device': devices[0]['id'] if devices else None
        }
    else:
        return {
            'connected': False,
            'devices': []
        }

@app.route('/api/device/info')
async def device_info(request):
    """API: Información del dispositivo"""
    info = adb_manager.get_device_info()
    
    if info:
        return {
            'success': True,
            'info': info
        }
    else:
        return {
            'success': False,
            'error': 'No se pudo obtener información del dispositivo'
        }

@app.route('/api/device/shell', methods=['POST'])
async def shell_command(request):
    """API: Ejecutar comando shell"""
    data = request.json
    if not data or 'command' not in data:
        return {
            'success': False,
            'error': 'Comando no especificado'
        }
    
    result = adb_manager.execute_shell_command(data['command'])
    
    return {
        'success': 'error' not in result,
        'output': result.get('output', ''),
        'error': result.get('error')
    }

@app.route('/api/device/reboot', methods=['POST'])
async def reboot_device(request):
    """API: Reiniciar dispositivo"""
    result = adb_manager.reboot_device()
    return result

@app.route('/api/adb/status')
async def adb_status(request):
    """API: Estado de ADB"""
    return {
        'available': adb_manager.is_available(),
        'path': adb_manager.adb_path
    }

# Terminal API Endpoints
@app.route('/api/terminal/create', methods=['POST'])
async def create_terminal(request):
    """API: Create new terminal session"""
    data = request.json or {}
    device_id = data.get('device_id')
    
    session_id = terminal_manager.create_session(device_id)
    
    if session_id:
        return {
            'success': True,
            'session_id': session_id
        }
    else:
        return {
            'success': False,
            'error': 'No se pudo crear la sesión terminal'
        }

@app.route('/api/terminal/<session_id>/write', methods=['POST'])
async def write_terminal(request, session_id):
    """API: Write to terminal session"""
    data = request.json
    if not data or 'input' not in data:
        return {'success': False, 'error': 'Input requerido'}
    
    success = terminal_manager.write_to_session(session_id, data['input'])
    
    return {
        'success': success,
        'error': 'Sesión no encontrada o inactiva' if not success else None
    }

@app.route('/api/terminal/<session_id>/resize', methods=['POST'])
async def resize_terminal(request, session_id):
    """API: Resize terminal session"""
    data = request.json
    if not data or 'rows' not in data or 'cols' not in data:
        return {'success': False, 'error': 'Rows y cols requeridos'}
    
    success = terminal_manager.resize_session(session_id, data['rows'], data['cols'])
    
    return {
        'success': success,
        'error': 'Sesión no encontrada o inactiva' if not success else None
    }

@app.route('/api/terminal/<session_id>/output')
async def get_terminal_output(request, session_id):
    """API: Get terminal output"""
    session = terminal_manager.get_session(session_id)
    
    if session:
        output = session.get_buffer()
        session.clear_buffer()
        
        return {
            'success': True,
            'output': output,
            'active': session.active
        }
    else:
        return {
            'success': False,
            'error': 'Sesión no encontrada'
        }

@app.route('/api/terminal/<session_id>/close', methods=['POST'])
async def close_terminal(request, session_id):
    """API: Close terminal session"""
    terminal_manager.close_session(session_id)
    
    return {
        'success': True
    }

@app.route('/api/terminal/sessions')
async def list_terminal_sessions(request):
    """API: List active terminal sessions"""
    sessions = terminal_manager.get_active_sessions()
    
    return {
        'success': True,
        'sessions': sessions
    }

@app.errorhandler(404)
async def not_found(request):
    """Manejador de 404"""
    return {'error': 'Not found'}, 404

@app.errorhandler(500)
async def server_error(request):
    """Manejador de 500"""
    return {'error': 'Internal server error'}, 500

def main():
    """Función principal"""
    print("🚀 Iniciando UBTool - Ubuntu Touch Connection Tool")
    print(f"🌐 Servidor disponible en: http://{HOST}:{PORT}")
    
    # Verificar ADB
    if not adb_manager.is_available():
        print("⚠️  ADB no está disponible. Algunas funciones no funcionarán.")
        print("   Por favor instala Android SDK Platform Tools")
    else:
        print(f"✅ ADB encontrado en: {adb_manager.adb_path}")
    
    # Iniciar servidor
    try:
        app.run(host=HOST, port=PORT, debug=DEBUG)
    except KeyboardInterrupt:
        print("\n👋 Deteniendo UBTool...")
    except Exception as e:
        print(f"❌ Error al iniciar servidor: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
