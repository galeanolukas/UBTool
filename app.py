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
import mimetypes
import re
import urllib.parse
import base64
from threading import Thread

from microdot import Microdot
from microdot.jinja import Template
from microdot.cors import CORS

# Import terminal manager
from terminal_manager import TerminalManager

try:
    import humanize
except Exception:
    humanize = None

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
                ('device_name', 'ro.product.name'),
                ('device', 'ro.product.device'),
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

            # Fallback for battery percentage (Ubuntu Touch / non-standard dumpsys)
            if not info.get('battery') or info.get('battery') in {'N/A', 'Timeout'}:
                fallback_battery = self._get_battery_percentage_sysfs(device_id)
                if fallback_battery:
                    info['battery'] = fallback_battery

            # Get memory info
            try:
                result = subprocess.run([
                    self.adb_path, '-s', device_id, 'shell',
                    "free -h 2>/dev/null || free"
                ], capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    info['memory'] = self._parse_free_output(result.stdout)
                else:
                    info['memory'] = None
            except subprocess.TimeoutExpired:
                info['memory'] = None

            # Get storage info
            try:
                result = subprocess.run([
                    self.adb_path, '-s', device_id, 'shell',
                    "df -h 2>/dev/null || df"
                ], capture_output=True, text=True, timeout=10)
                if result.returncode == 0 and result.stdout.strip():
                    info['storage'] = self._parse_df_output(result.stdout)
                else:
                    info['storage'] = None
            except subprocess.TimeoutExpired:
                info['storage'] = None
            
            # Get OS info
            try:
                result = subprocess.run([
                    self.adb_path, '-s', device_id, 'shell',
                    'uname -a'
                ], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    uname_info = result.stdout.strip()
                    info['os_info'] = uname_info
                    # Parse OS name and version from uname
                    if 'Ubuntu' in uname_info:
                        info['os_name'] = 'Ubuntu Touch'
                        # Try to extract version
                        import re
                        version_match = re.search(r'Ubuntu (\d+\.\d+)', uname_info)
                        if version_match:
                            info['os_version'] = version_match.group(1)
                    else:
                        info['os_name'] = uname_info
                else:
                    info['os_info'] = 'N/A'
                    info['os_name'] = 'N/A'
                    info['os_version'] = 'N/A'
            except subprocess.TimeoutExpired:
                info['os_info'] = 'Timeout'
                info['os_name'] = 'Timeout'
                info['os_version'] = 'Timeout'

            # Get IP address
            try:
                result = subprocess.run([
                    self.adb_path, '-s', device_id, 'shell',
                    "ip route get 1 2>/dev/null | awk '{print $7}' || ip addr show 2>/dev/null | grep 'inet ' | head -1 | awk '{print $2}' | cut -d'/' -f1 || hostname -I 2>/dev/null || echo 'N/A'"
                ], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    ip = result.stdout.strip()
                    info['ip_address'] = ip if ip and ip != 'N/A' else 'N/A'
                else:
                    info['ip_address'] = 'N/A'
            except subprocess.TimeoutExpired:
                info['ip_address'] = 'Timeout'
            
            return info
            
        except Exception as e:
            print(f"Error getting device info: {e}")
            return None
    
    def _parse_battery_info(self, battery_output):
        """Parsea la información de la batería"""
        try:
            text = battery_output or ''
            level = None
            scale = None

            # Common outputs:
            # level: 44
            # scale: 100
            # or sometimes key=value
            m_level = re.search(r'\blevel\b\s*[:=]\s*(\d+)', text, flags=re.IGNORECASE)
            if m_level:
                try:
                    level = int(m_level.group(1))
                except Exception:
                    level = None

            m_scale = re.search(r'\bscale\b\s*[:=]\s*(\d+)', text, flags=re.IGNORECASE)
            if m_scale:
                try:
                    scale = int(m_scale.group(1))
                except Exception:
                    scale = None

            # Some systems expose percentage directly
            m_pct = re.search(r'\b(percent|percentage)\b\s*[:=]\s*(\d+)', text, flags=re.IGNORECASE)
            if m_pct:
                try:
                    return f"{int(m_pct.group(2))}%"
                except Exception:
                    pass

            if level is None:
                return 'N/A'

            if scale and scale > 0:
                pct = round((level / scale) * 100)
                return f"{pct}%"

            return f"{level}%"
        except:
            return 'N/A'

    def _get_battery_percentage_sysfs(self, device_id):
        """Fallback: intenta leer porcentaje desde /sys/class/power_supply/*/capacity"""
        try:
            cmd = (
                "cat /sys/class/power_supply/battery/capacity 2>/dev/null "
                "|| cat /sys/class/power_supply/BAT0/capacity 2>/dev/null "
                "|| (ls /sys/class/power_supply 2>/dev/null | while read d; do "
                "cat /sys/class/power_supply/$d/capacity 2>/dev/null && break; "
                "done)"
            )
            result = subprocess.run([
                self.adb_path, '-s', device_id, 'shell', cmd
            ], capture_output=True, text=True, timeout=5)

            if result.returncode != 0:
                return None

            raw = (result.stdout or '').strip().splitlines()
            if not raw:
                return None

            first = raw[0].strip()
            if not first:
                return None

            m = re.search(r'(\d+)', first)
            if not m:
                return None

            pct = int(m.group(1))
            if pct < 0 or pct > 100:
                return None

            return f"{pct}%"
        except Exception:
            return None

    def _parse_free_output(self, free_output):
        try:
            lines = [l.strip() for l in free_output.split('\n') if l.strip()]
            mem_line = None
            for l in lines:
                if l.lower().startswith('mem:') or l.lower().startswith('mem '):
                    mem_line = l
                    break
            if not mem_line:
                return None

            parts = mem_line.replace('\t', ' ').split()
            if len(parts) < 4:
                return None

            def _safe_get(i):
                return parts[i] if i < len(parts) else None

            return {
                'total': _safe_get(1),
                'used': _safe_get(2),
                'free': _safe_get(3),
                'available': _safe_get(6) if len(parts) >= 7 else _safe_get(3)
            }
        except Exception:
            return None

    def _parse_df_output(self, df_output):
        try:
            lines = [l.rstrip() for l in df_output.split('\n') if l.strip()]
            if not lines:
                return None

            out = []
            for line in lines[1:]:
                parts = line.split()
                if len(parts) < 6:
                    continue
                out.append({
                    'filesystem': parts[0],
                    'size': parts[1],
                    'used': parts[2],
                    'avail': parts[3],
                    'use_percent': parts[4],
                    'mount': parts[5]
                })

            if not out:
                return None

            preferred_mounts = {'/data', '/userdata', '/', '/home', '/home/phablet'}
            preferred = [e for e in out if e.get('mount') in preferred_mounts]
            return {
                'primary': preferred[0] if preferred else out[0],
                'entries': out
            }
        except Exception:
            return None
    
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


@app.route('/apps')
async def apps_page(request):
    """Página de apps instaladas"""
    from microdot import Response
    html_content = render_template('apps.html')
    return Response(html_content, headers={'Content-Type': 'text/html; charset=utf-8'})


@app.route('/dev-env')
async def dev_env_page(request):
    """Página de preparación de entorno de desarrollo"""
    from microdot import Response
    html_content = render_template('dev-env.html')
    return Response(html_content, headers={'Content-Type': 'text/html; charset=utf-8'})


@app.route('/static/<path:path>')
def static_files(request, path):
    """Servir archivos estáticos desde ./static"""
    from microdot import Response

    static_root = os.path.abspath('static')
    requested_path = os.path.abspath(os.path.join(static_root, path))

    # Prevent path traversal
    if not (requested_path == static_root or requested_path.startswith(static_root + os.sep)):
        return Response('Not found', status_code=404)

    if not os.path.isfile(requested_path):
        return Response('Not found', status_code=404)

    content_type, _ = mimetypes.guess_type(requested_path)
    if not content_type:
        content_type = 'application/octet-stream'

    with open(requested_path, 'rb') as f:
        data = f.read()

    return Response(data, headers={'Content-Type': content_type})

@app.route('/api/terminal/sessions', methods=['GET'])
def list_terminal_sessions():
    """Listar todas las sesiones de terminal activas"""
    try:
        sessions = []
        for session_id, session in terminal_manager.sessions.items():
            if session.active:
                sessions.append({
                    'session_id': session_id,
                    'device_id': session.device_id,
                    'created_at': time.time()
                })
        
        return json.dumps({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })


@app.route('/api/devtools/list_packages')
async def list_packages(request):
    """API: Listar paquetes instalados en el entorno virtual"""
    try:
        adb_bin = adb_manager.adb_path or 'adb'
        global_venv_python = "/home/phablet/.ubtool/venv/bin/python"
        
        # List packages using pip list
        cmd = f"{global_venv_python} -m pip list --format=json"
        result = subprocess.run([adb_bin, 'shell', cmd], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            try:
                packages_data = json.loads(result.stdout)
                packages = []
                
                for pkg in packages_data:
                    packages.append({
                        'name': pkg.get('name', 'Unknown'),
                        'version': pkg.get('version', 'N/A')
                    })
                
                return {
                    'success': True,
                    'packages': packages
                }
            except json.JSONDecodeError:
                # Fallback to parsing plain text
                lines = result.stdout.strip().split('\n')
                packages = []
                for line in lines:
                    if '==' in line:
                        name, version = line.split('==')
                        packages.append({
                            'name': name.strip(),
                            'version': version.strip() if version else 'N/A'
                        })
                
                return {
                    'success': True,
                    'packages': packages
                }
        else:
            return {
                'success': False,
                'error': f'Error listando paquetes: {result.stderr}'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@app.route('/api/devtools/install_package', methods=['POST'])
async def install_package(request):
    """API: Instalar un paquete en el entorno virtual"""
    try:
        data = request.json or {}
        package_name = data.get('package_name', '').strip()
        
        if not package_name:
            return {
                'success': False,
                'error': 'Nombre del paquete requerido'
            }
        
        adb_bin = adb_manager.adb_path or 'adb'
        global_venv_pip = "/home/phablet/.ubtool/venv/bin/pip"
        
        # Install package
        cmd = f"{global_venv_pip} install {package_name}"
        result = subprocess.run([adb_bin, 'shell', cmd], capture_output=True, text=True, timeout=180)
        
        if result.returncode == 0:
            return {
                'success': True,
                'message': f'Paquete {package_name} instalado exitosamente'
            }
        else:
            return {
                'success': False,
                'error': f'Error instalando {package_name}: {result.stderr}'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@app.route('/api/devtools/prepare_env', methods=['POST'])
async def prepare_dev_environment(request):
    """API: Preparar entorno de desarrollo completo"""
    try:
        adb_bin = adb_manager.adb_path or 'adb'
        
        # Commands to prepare development environment
        commands = [
            # Update package lists
            "apt update",
            
            # Install essential development tools
            "apt install -y python3 python3-pip python3-venv build-essential git curl wget",
            
            # Create global virtual environment directory
            "mkdir -p /home/phablet/.ubtool",
            
            # Create virtual environment
            "python3 -m venv /home/phablet/.ubtool/venv",
            
            # Upgrade pip in virtual environment
            "/home/phablet/.ubtool/venv/bin/pip install --upgrade pip",
            
            # Install essential packages
            "/home/phablet/.ubtool/venv/bin/pip install flask fastapi microdot jinja2 requests"
        ]
        
        for cmd in commands:
            result = subprocess.run([adb_bin, 'shell', cmd], capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                return {
                    'success': False,
                    'error': f'Error en comando: {cmd}',
                    'details': result.stderr
                }
        
        return {
            'success': True,
            'message': 'Entorno de desarrollo preparado exitosamente',
            'venv_path': '/home/phablet/.ubtool/venv',
            'python_path': '/home/phablet/.ubtool/venv/bin/python',
            'pip_path': '/home/phablet/.ubtool/venv/bin/pip'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


@app.route('/api/devtools/venv_status')
async def venv_status(request):
    """API: Verificar estado del entorno virtual global"""
    try:
        # Verificar si el directorio del venv global existe
        check_cmd = "test -d /home/phablet/.ubtool/venv && echo 'exists' || echo 'not_exists'"
        result = subprocess.run(['adb', 'shell', check_cmd], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and 'exists' in result.stdout:
            # Verificar si python está disponible en el venv
            python_check = "test -f /home/phablet/.ubtool/venv/bin/python && echo 'ready' || echo 'incomplete'"
            python_result = subprocess.run(['adb', 'shell', python_check], capture_output=True, text=True, timeout=10)
            
            # Verificar si pip está disponible en el venv
            pip_check = "test -f /home/phablet/.ubtool/venv/bin/pip && echo 'ready' || echo 'incomplete'"
            pip_result = subprocess.run(['adb', 'shell', pip_check], capture_output=True, text=True, timeout=10)
            
            if python_result.returncode == 0 and 'ready' in python_result.stdout and pip_result.returncode == 0 and 'ready' in pip_result.stdout:
                return json.dumps({
                    'success': True,
                    'status': 'ready',
                    'message': 'Entorno global listo para usar',
                    'venv_path': '/home/phablet/.ubtool/venv',
                    'python_path': '/home/phablet/.ubtool/venv/bin/python',
                    'pip_path': '/home/phablet/.ubtool/venv/bin/pip'
                })
            else:
                return json.dumps({
                    'success': True,
                    'status': 'incomplete',
                    'message': 'Entorno global incompleto',
                    'venv_path': '/home/phablet/.ubtool/venv',
                    'python_path': '/home/phablet/.ubtool/venv/bin/python',
                    'pip_path': '/home/phablet/.ubtool/venv/bin/pip'
                })
        else:
            return json.dumps({
                'success': True,
                'status': 'not_created',
                'message': 'Entorno global no creado',
                'venv_path': '/home/phablet/.ubtool/venv',
                'python_path': 'N/A',
                'pip_path': 'N/A'
            })
            
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })


@app.route('/api/files/list')
async def list_device_files(request):
    """API: Listar archivos del dispositivo (File Manager)."""
    try:
        if not adb_manager.is_available():
            return {'success': False, 'error': 'ADB no disponible'}

        devices = adb_manager.get_devices()
        if not devices:
            return {'success': False, 'error': 'No hay dispositivos conectados'}

        device_id = devices[0]['id']

        qs = getattr(request, 'query_string', b'')
        if isinstance(qs, (bytes, bytearray)):
            qs = qs.decode('utf-8', errors='ignore')
        params = urllib.parse.parse_qs(qs or '')
        path = (params.get('path', [None])[0] or '/home/phablet').strip()
        if not path.startswith('/'):
            path = '/' + path

        adb_bin = adb_manager.adb_path or 'adb'

        py_code = (
            "import os,sys,json\n"
            "p=sys.argv[1] if len(sys.argv)>1 else '/home/phablet'\n"
            "p=os.path.normpath(p)\n"
            "out={'path':p,'parent':os.path.dirname(p) if p!='/' else None,'entries':[]}\n"
            "try:\n"
            "  with os.scandir(p) as it:\n"
            "    for e in it:\n"
            "      try:\n"
            "        st=e.stat(follow_symlinks=False)\n"
            "        size=int(st.st_size)\n"
            "        mtime=int(st.st_mtime)\n"
            "      except Exception:\n"
            "        size=None; mtime=None\n"
            "      out['entries'].append({'name':e.name,'is_dir':e.is_dir(follow_symlinks=False),'size':size,'mtime':mtime})\n"
            "  out['entries'].sort(key=lambda x:(not x.get('is_dir',False), x.get('name','').lower()))\n"
            "  print(json.dumps(out))\n"
            "except Exception as ex:\n"
            "  print(json.dumps({'error':str(ex),'path':p}), end='')\n"
        )

        result = subprocess.run(
            [adb_bin, '-s', device_id, 'shell', 'python3', '-c', py_code, path],
            capture_output=True,
            text=True,
            timeout=20
        )

        if result.returncode != 0:
            return {
                'success': False,
                'error': (result.stderr or result.stdout or '').strip() or 'Error al listar archivos'
            }

        raw = (result.stdout or '').strip()
        if raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict) and data.get('error'):
                    return {'success': False, 'error': data.get('error'), 'path': data.get('path')}

                # Add human readable sizes
                for e in data.get('entries', []) if isinstance(data, dict) else []:
                    sz = e.get('size')
                    if sz is None:
                        e['size_human'] = None
                    else:
                        if humanize:
                            e['size_human'] = humanize.naturalsize(sz, binary=True)
                        else:
                            e['size_human'] = str(sz)

                return {'success': True, 'data': data}
            except Exception:
                # Fall through to ls fallback
                pass

        # If python3 produced no usable output, try to surface stderr and fallback to ls
        stderr = (result.stderr or '').strip()

        safe_path = path.replace("'", "'\\''")
        ls_cmd = (
            f"p='{safe_path}'; "
            "ls -la \"$p\" 2>/dev/null || ls -la 2>/dev/null"
        )
        ls = subprocess.run(
            [adb_bin, '-s', device_id, 'shell', ls_cmd],
            capture_output=True,
            text=True,
            timeout=20
        )

        ls_out = (ls.stdout or '').splitlines()
        if not ls_out:
            err = (ls.stderr or stderr or '').strip() or 'Respuesta vacía del dispositivo'
            return {'success': False, 'error': err}

        entries = []
        for line in ls_out:
            line = line.rstrip('\n')
            if not line or line.startswith('total'):
                continue
            parts = line.split(None, 8)
            if len(parts) < 9:
                continue
            mode = parts[0]
            name = parts[8]
            try:
                size = int(parts[4])
            except Exception:
                size = None
            is_dir = mode.startswith('d')
            if name in {'.', '..'}:
                continue
            item = {
                'name': name,
                'is_dir': is_dir,
                'size': size,
                'mtime': None
            }
            if size is not None:
                item['size_human'] = humanize.naturalsize(size, binary=True) if humanize else str(size)
            else:
                item['size_human'] = None
            entries.append(item)

        payload = {
            'path': path,
            'parent': os.path.dirname(path) if path != '/' else None,
            'entries': entries
        }

        if stderr:
            payload['warning'] = stderr

        return {'success': True, 'data': payload}
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Timeout al listar archivos'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.route('/api/files/raw')
async def get_device_file_raw(request):
    """API: Obtener archivo del dispositivo como binario (viewer/descarga)."""
    try:
        from microdot import Response

        if not adb_manager.is_available():
            return Response(b'ADB no disponible', status_code=400)

        devices = adb_manager.get_devices()
        if not devices:
            return Response(b'No hay dispositivos conectados', status_code=400)

        device_id = devices[0]['id']

        qs = getattr(request, 'query_string', b'')
        if isinstance(qs, (bytes, bytearray)):
            qs = qs.decode('utf-8', errors='ignore')
        params = urllib.parse.parse_qs(qs or '')
        path = (params.get('path', [None])[0] or '').strip()
        if not path:
            return Response(b'path requerido', status_code=400)

        adb_bin = adb_manager.adb_path or 'adb'

        safe_path = path.replace("'", "'\\''")
        cat_cmd = f"cat '{safe_path}'"
        result = subprocess.run(
            [adb_bin, '-s', device_id, 'exec-out', 'sh', '-c', cat_cmd],
            capture_output=True,
            timeout=30
        )

        if result.returncode != 0:
            msg = (result.stderr or b'').strip() or b'Error al leer archivo'
            return Response(msg, status_code=404)

        content_type, _ = mimetypes.guess_type(path)
        if not content_type:
            content_type = 'application/octet-stream'

        return Response(result.stdout or b'', headers={'Content-Type': content_type})
    except subprocess.TimeoutExpired:
        from microdot import Response
        return Response(b'Timeout al leer archivo', status_code=408)
    except Exception as e:
        from microdot import Response
        return Response(str(e).encode('utf-8', errors='ignore'), status_code=500)


@app.route('/api/files/text')
async def get_device_file_text(request):
    """API: Obtener archivo de texto del dispositivo (para editor)."""
    try:
        if not adb_manager.is_available():
            return {'success': False, 'error': 'ADB no disponible'}

        devices = adb_manager.get_devices()
        if not devices:
            return {'success': False, 'error': 'No hay dispositivos conectados'}

        device_id = devices[0]['id']

        qs = getattr(request, 'query_string', b'')
        if isinstance(qs, (bytes, bytearray)):
            qs = qs.decode('utf-8', errors='ignore')
        params = urllib.parse.parse_qs(qs or '')
        path = (params.get('path', [None])[0] or '').strip()
        if not path:
            return {'success': False, 'error': 'path requerido'}

        # size limit (bytes)
        max_bytes = 200_000

        adb_bin = adb_manager.adb_path or 'adb'
        safe_path = path.replace("'", "'\\''")
        cmd = f"cat '{safe_path}'"
        result = subprocess.run(
            [adb_bin, '-s', device_id, 'exec-out', 'sh', '-c', cmd],
            capture_output=True,
            timeout=20
        )

        if result.returncode != 0:
            err = (result.stderr or b'').decode('utf-8', errors='ignore').strip() or 'Error al leer archivo'
            return {'success': False, 'error': err}

        data = result.stdout or b''
        if len(data) > max_bytes:
            return {'success': False, 'error': f'Archivo demasiado grande para editar (>{max_bytes} bytes)'}

        text = data.decode('utf-8', errors='replace')
        mime, _ = mimetypes.guess_type(path)
        return {'success': True, 'path': path, 'mime': mime or 'text/plain', 'content': text}
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Timeout al leer archivo'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.route('/api/files/write', methods=['POST'])
async def write_device_file_text(request):
    """API: Guardar archivo de texto en el dispositivo."""
    try:
        if not adb_manager.is_available():
            return {'success': False, 'error': 'ADB no disponible'}

        devices = adb_manager.get_devices()
        if not devices:
            return {'success': False, 'error': 'No hay dispositivos conectados'}

        device_id = devices[0]['id']
        payload = request.json or {}
        path = (payload.get('path') or '').strip()
        content = payload.get('content')
        if not path:
            return {'success': False, 'error': 'path requerido'}
        if content is None:
            return {'success': False, 'error': 'content requerido'}

        raw = content.encode('utf-8')
        if len(raw) > 200_000:
            return {'success': False, 'error': 'Contenido demasiado grande'}

        b64 = base64.b64encode(raw).decode('ascii')
        adb_bin = adb_manager.adb_path or 'adb'
        safe_path = path.replace("'", "'\\''")

        # Requires base64 on device
        cmd = f"printf %s '{b64}' | base64 -d > '{safe_path}'"
        result = subprocess.run(
            [adb_bin, '-s', device_id, 'shell', 'sh', '-c', cmd],
            capture_output=True,
            text=True,
            timeout=20
        )

        if result.returncode != 0:
            err = (result.stderr or result.stdout or '').strip() or 'Error al guardar archivo'
            return {'success': False, 'error': err}

        return {'success': True, 'path': path}
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'Timeout al guardar archivo'}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@app.route('/api/devtools/prepare_env', methods=['POST'])
def prepare_dev_environment(request):
    """Preparar entorno de desarrollo en el dispositivo (python3/pip/virtualenv)."""
    try:
        adb_bin = adb_manager.adb_path or 'adb'

        global_venv_dir = '/home/phablet/.ubtool/venv'
        global_venv_pip = f'{global_venv_dir}/bin/pip'

        def run_shell(cmd, timeout=60):
            return subprocess.run([adb_bin, 'shell', cmd], capture_output=True, text=True, timeout=timeout)

        details = {
            'python': {'available': False, 'version': None},
            'pip': {'available': False, 'version': None},
            'virtualenv': {'available': False},
            'actions': []
        }

        py = run_shell('python3 --version', timeout=15)
        if py.returncode == 0 and (py.stdout or py.stderr):
            details['python']['available'] = True
            details['python']['version'] = (py.stdout or py.stderr).strip()
        else:
            return json.dumps({
                'success': False,
                'error': 'python3 no disponible en el dispositivo',
                'details': details
            })

        # pip: prefer python3 -m pip
        pip = run_shell('python3 -m pip --version', timeout=20)
        if pip.returncode == 0 and (pip.stdout or pip.stderr):
            details['pip']['available'] = True
            details['pip']['version'] = (pip.stdout or pip.stderr).strip()
        else:
            # try ensurepip (may not exist on all builds)
            ensure = run_shell('python3 -m ensurepip --user', timeout=60)
            details['actions'].append({
                'step': 'ensurepip',
                'return_code': ensure.returncode,
                'stdout': (ensure.stdout or '').strip(),
                'stderr': (ensure.stderr or '').strip()
            })

            pip = run_shell('python3 -m pip --version', timeout=20)
            if pip.returncode == 0 and (pip.stdout or pip.stderr):
                details['pip']['available'] = True
                details['pip']['version'] = (pip.stdout or pip.stderr).strip()

        if not details['pip']['available']:
            return json.dumps({
                'success': False,
                'error': 'pip no disponible (python3 -m pip falla y ensurepip no funcionó)',
                'details': details
            })

        # Upgrade pip/setuptools/wheel (best effort)
        up = run_shell('python3 -m pip install --user -U pip setuptools wheel', timeout=180)
        details['actions'].append({
            'step': 'upgrade_pip',
            'return_code': up.returncode,
            'stdout': (up.stdout or '').strip(),
            'stderr': (up.stderr or '').strip()
        })

        # virtualenv
        venv_check = run_shell('python3 -m virtualenv --version', timeout=15)
        if venv_check.returncode == 0:
            details['virtualenv']['available'] = True
        else:
            inst = run_shell('python3 -m pip install --user virtualenv', timeout=180)
            details['actions'].append({
                'step': 'install_virtualenv',
                'return_code': inst.returncode,
                'stdout': (inst.stdout or '').strip(),
                'stderr': (inst.stderr or '').strip()
            })

            venv_check = run_shell('python3 -m virtualenv --version', timeout=15)
            details['virtualenv']['available'] = venv_check.returncode == 0

        if not details['virtualenv']['available']:
            return json.dumps({
                'success': False,
                'error': 'virtualenv no se pudo instalar/verificar',
                'details': details
            })

        # Global venv (shared across all webapps)
        mk = run_shell("mkdir -p /home/phablet/.ubtool", timeout=20)
        details['actions'].append({
            'step': 'mkdir_global_dir',
            'return_code': mk.returncode,
            'stdout': (mk.stdout or '').strip(),
            'stderr': (mk.stderr or '').strip()
        })

        # Create venv if it does not exist
        venv_exists = run_shell(f"test -x {global_venv_dir}/bin/python && echo yes || echo no", timeout=10)
        if (venv_exists.stdout or '').strip() != 'yes':
            mkvenv = run_shell(f"python3 -m virtualenv {global_venv_dir}", timeout=180)
            details['actions'].append({
                'step': 'create_global_venv',
                'return_code': mkvenv.returncode,
                'stdout': (mkvenv.stdout or '').strip(),
                'stderr': (mkvenv.stderr or '').strip()
            })
            if mkvenv.returncode != 0:
                return json.dumps({
                    'success': False,
                    'error': 'No se pudo crear el entorno virtual global',
                    'details': details
                })

        # Upgrade pip/setuptools/wheel inside venv
        up_venv = run_shell(f"{global_venv_pip} install -U pip setuptools wheel", timeout=180)
        details['actions'].append({
            'step': 'upgrade_global_venv_pip',
            'return_code': up_venv.returncode,
            'stdout': (up_venv.stdout or '').strip(),
            'stderr': (up_venv.stderr or '').strip()
        })

        # Install shared frameworks (best effort)
        install_fw = run_shell(f"{global_venv_pip} install -U microdot jinja2 flask gunicorn fastapi uvicorn", timeout=300)
        details['actions'].append({
            'step': 'install_frameworks_global_venv',
            'return_code': install_fw.returncode,
            'stdout': (install_fw.stdout or '').strip(),
            'stderr': (install_fw.stderr or '').strip()
        })

        return json.dumps({
            'success': True,
            'message': 'Entorno listo (python3/pip/virtualenv + venv global)',
            'details': details,
            'global_venv': global_venv_dir
        })
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })

@app.route('/api/devtools/check', methods=['GET'])
def check_dev_tools(request):
    """Verificar disponibilidad de herramientas de desarrollo en el dispositivo"""
    try:
        # Verificar Python
        python_check = subprocess.run(
            ['adb', 'shell', 'python3 --version'],
            capture_output=True, text=True, timeout=10
        )
        python_version = python_check.stdout.strip() if python_check.returncode == 0 else None
        
        # Verificar pip
        pip_check = subprocess.run(
            ['adb', 'shell', 'pip3 --version'],
            capture_output=True, text=True, timeout=10
        )
        pip_version = pip_check.stdout.strip() if pip_check.returncode == 0 else None
        
        # Verificar virtualenv
        venv_check = subprocess.run(
            ['adb', 'shell', 'which virtualenv'],
            capture_output=True, text=True, timeout=10
        )
        virtualenv_path = venv_check.stdout.strip() if venv_check.returncode == 0 else None
        
        # Verificar espacio disponible
        space_check = subprocess.run(
            ['adb', 'shell', "df -h /home/phablet | tail -1 | awk '{print $4}'"],
            capture_output=True, text=True, timeout=10
        )
        available_space = space_check.stdout.strip() if space_check.returncode == 0 else None
        
        # Verificar memoria
        memory_check = subprocess.run(
            ['adb', 'shell', "free -h | grep '^Mem:' | awk '{print $7}'"],
            capture_output=True, text=True, timeout=10
        )
        available_memory = memory_check.stdout.strip() if memory_check.returncode == 0 else None
        
        return json.dumps({
            'success': True,
            'tools': {
                'python': {
                    'available': python_version is not None,
                    'version': python_version
                },
                'pip': {
                    'available': pip_version is not None,
                    'version': pip_version
                },
                'virtualenv': {
                    'available': virtualenv_path is not None,
                    'path': virtualenv_path
                }
            },
            'resources': {
                'disk_space': available_space,
                'memory': available_memory
            }
        })
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })

def get_microdot_app_content(app_name, framework, app_path, python_path):
    """Generate Microdot app.py content"""
    return f'''#!/usr/bin/env python3
"""
{app_name} - Web Application
Created with UBTool using {framework} framework
"""

from microdot import Microdot
from microdot.jinja import Template
import os

# Initialize app
app = Microdot()

# Configuration
DEBUG = True
HOST = '0.0.0.0'
PORT = 8080

@app.route('/')
async def index(request):
    """Main page"""
    template = Template("""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name }}</title>
    <link rel="stylesheet" href="/static/css/style.css">
</head>
<body>
    <div class="container">
        <h1>{{ app_name }}</h1>
        <p>Aplicacion funcionando con Microdot!</p>
        <p><strong>Ruta:</strong> {app_path}</p>
        <p><strong>Servidor:</strong> {python_path} app.py</p>
        
        <div class="api-info">
            <h2>API Endpoints</h2>
            <ul>
                <li><code>GET /</code> - Página principal</li>
                <li><code>GET /api/status</code> - Estado del servidor</li>
                <li><code>GET /api/info</code> - Información de la app</li>
            </ul>
        </div>
        
        <button class="btn" onclick="checkAPI()">Probar API</button>
        <div id="api-result" style="margin-top: 20px;"></div>
    </div>
    
    <script src="/static/js/app.js"></script>
    <script>
        function checkAPI() {{
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {{
                    document.getElementById('api-result').innerHTML = 
                        '<h3>API Response:</h3><pre>' + JSON.stringify(data, null, 2) + '</pre>';
                }})
                .catch(error => {{
                    document.getElementById('api-result').innerHTML = 
                        '<h3>Error:</h3><p>' + error.message + '</p>';
                }});
        }}
    </script>
</body>
</html>
    """)
    
    return template.render(app_name=app_name)

@app.route('/api/status')
async def api_status(request):
    """API status endpoint"""
    return {{
        'status': 'running',
        'app': app_name,
        'framework': framework,
        'version': '1.0.0',
        'endpoints': [
            '/',
            '/api/status',
            '/api/info'
        ]
    }}

@app.route('/api/info')
async def api_info(request):
    """API info endpoint"""
    return {{
        'app_name': app_name,
        'framework': framework,
        'python_path': '{python_path}',
        'app_path': '{app_path}',
        'description': 'App created with UBTool',
        'features': [
            'Microdot framework',
            'Jinja2 templates',
            'Static files support',
            'REST API endpoints'
        ]
    }}

if __name__ == '__main__':
    print(f"Starting {{{{ app_name }}}} on http://{{{{ HOST }}}}:{{{{ PORT }}}}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
'''

def get_flask_app_content(app_name, framework, app_path, python_path):
    """Generate Flask app.py content"""
    return f'''#!/usr/bin/env python3
"""
{app_name} - Web Application
Created with UBTool using {framework} framework
"""

from flask import Flask, render_template, jsonify
import os

# Initialize app
app = Flask(__name__)

# Configuration
DEBUG = True
HOST = '0.0.0.0'
PORT = 8080

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html', app_name=app_name)

@app.route('/api/status')
def api_status():
    """API status endpoint"""
    return jsonify({{
        'status': 'running',
        'app': app_name,
        'framework': framework,
        'version': '1.0.0',
        'endpoints': [
            '/',
            '/api/status',
            '/api/info'
        ]
    }})

@app.route('/api/info')
def api_info():
    """API info endpoint"""
    return jsonify({{
        'app_name': app_name,
        'framework': framework,
        'python_path': '{python_path}',
        'app_path': '{app_path}',
        'description': 'App created with UBTool',
        'features': [
            'Flask framework',
            'Jinja2 templates',
            'Static files support',
            'REST API endpoints'
        ]
    }})

if __name__ == '__main__':
    print(f"Starting {{{{ app_name }}}} on http://{{{{ HOST }}}}:{{{{ PORT }}}}")
    app.run(host=HOST, port=PORT, debug=DEBUG)
'''

def get_fastapi_app_content(app_name, framework, app_path, python_path):
    """Generate FastAPI app.py content"""
    return f'''#!/usr/bin/env python3
"""
{app_name} - Web Application
Created with UBTool using {framework} framework
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
import os

# Initialize app
app = FastAPI(title=app_name)

# Configuration
DEBUG = True
HOST = '0.0.0.0'
PORT = 8080

# Setup templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index(request: Request):
    """Main page"""
    return templates.TemplateResponse("index.html", {{"request": request, "app_name": app_name}})

@app.get("/api/status")
async def api_status():
    """API status endpoint"""
    return {{
        "status": "running",
        "app": app_name,
        "framework": framework,
        "version": "1.0.0",
        "endpoints": [
            "/",
            "/api/status",
            "/api/info"
        ]
    }}

@app.get("/api/info")
async def api_info():
    """API info endpoint"""
    return {{
        "app_name": app_name,
        "framework": framework,
        "python_path": "{python_path}",
        "app_path": "{app_path}",
        "description": "App created with UBTool",
        "features": [
            "FastAPI framework",
            "Jinja2 templates",
            "Static files support",
            "REST API endpoints",
            "Automatic OpenAPI docs"
        ]
    }}

if __name__ == '__main__':
    print(f"Starting {{{{ app_name }}}} on http://{{{{ HOST }}}}:{{{{ PORT }}}}")
    uvicorn.run(app, host=HOST, port=PORT, reload=DEBUG)
'''

@app.route('/api/devtools/create_env', methods=['POST'])
def create_virtual_env(request):
    """Crear app web usando un entorno virtual global (compartido)."""
    try:
        # Import configuration
        import config
        
        # Handle both JSON and FormData requests
        app_name = None
        framework = 'microdot'
        icon_file = None
        
        # Check if this is a FormData request (for file uploads)
        content_type = getattr(request, 'content_type', '')
        if content_type and 'multipart/form-data' in content_type:
            # Handle FormData request
            if hasattr(request, 'form') and request.form:
                app_name = request.form.get('app_name', '').strip()
                framework = request.form.get('framework', 'microdot').strip()
                # Handle file upload
                if hasattr(request, 'files') and request.files:
                    icon_file = request.files.get('icon')
        else:
            # Fallback to JSON for regular requests
            data = request.json or {}
            app_name = data.get('app_name', '').strip()
            framework = data.get('framework', 'microdot').strip()
        
        if not app_name:
            return json.dumps({
                'success': False,
                'error': 'Nombre de app requerido'
            })
        
        # Validar nombre de app
        if not re.match(r'^[a-zA-Z0-9_-]+$', app_name):
            return json.dumps({
                'success': False,
                'error': 'Nombre de app inválido. Solo letras, números, guiones y guiones bajos'
            })
        
        adb_bin = adb_manager.adb_path or 'adb'
        
        # Use configuration from config.py
        global_venv_python = config.GLOBAL_VENV_PYTHON
        global_venv_pip = config.GLOBAL_VENV_PIP
        app_path = f"{config.APPS_BASE_PATH}/{app_name}"

        # Ensure global venv exists
        chk = subprocess.run(
            [adb_bin, 'shell', f"test -x {global_venv_python}"],
            capture_output=True, text=True, timeout=10
        )
        if chk.returncode != 0:
            return json.dumps({
                'success': False,
                'error': 'Entorno global no encontrado. Ejecuta primero: Preparar entorno',
                'global_venv': config.GLOBAL_VENV_PATH
            })

        commands = [
            f"mkdir -p {app_path}",
            f"mkdir -p {app_path}/static",
            f"mkdir -p {app_path}/static/css", 
            f"mkdir -p {app_path}/static/js",
            f"mkdir -p {app_path}/static/images",
            f"mkdir -p {app_path}/templates",
        ]

        # Create basic static files
        css_content = '''/* Basic CSS for UBTool App */
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background: #f5f5f5;
}

.container {
    max-width: 800px;
    margin: 0 auto;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

h1 {
    color: #333;
    text-align: center;
}

.btn {
    background: #007bff;
    color: white;
    padding: 10px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
}

.btn:hover {
    background: #0056b3;
}
'''
        
        js_content = '''// Basic JavaScript for UBTool App
console.log('App loaded successfully!');

// Basic interaction
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded');
});
'''

        # Create static files
        commands.extend([
            f"echo '{css_content}' > {app_path}/static/css/style.css",
            f"echo '{js_content}' > {app_path}/static/js/app.js",
        ])

        # Handle icon file upload
        if icon_file:
            try:
                # Read file content and save to device
                icon_content = icon_file.read()
                icon_filename = icon_file.filename or 'icon.png'
                icon_path = f"{app_path}/static/images/{icon_filename}"
                
                # Create a temporary file and push it to device
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
                    temp_file.write(icon_content)
                    temp_file_path = temp_file.name
                
                # Create images directory and push file to device
                mkdir_cmd = f"mkdir -p {app_path}/static/images"
                subprocess.run([adb_bin, 'shell', mkdir_cmd], timeout=10)
                
                push_result = subprocess.run([
                    adb_bin, 'push', temp_file_path, icon_path
                ], capture_output=True, text=True, timeout=30)
                
                # Clean up temp file
                os.unlink(temp_file_path)
                
                if push_result.returncode != 0:
                    print(f"Warning: Failed to upload icon: {push_result.stderr}")
                else:
                    print(f"Icon uploaded successfully: {icon_path}")
                    
            except Exception as e:
                print(f"Warning: Error processing icon file: {e}")
                # Continue without icon if upload fails

        # Create basic template
        template_content = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ app_name or "Mi App" }}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <link rel="icon" href="{{ url_for('static', filename='images/icon.png') }}" type="image/x-icon">
</head>
<body>
    <div class="container">
        <h1>{{ app_name or "Mi App" }}</h1>
        <p>Aplicacion creada con UBTool usando el framework {framework}!</p>
        
        <div class="features">
            <h2>Caracteristicas</h2>
            <ul>
                <li>Estructura de directorios organizada</li>
                <li>Archivos estaticos (CSS, JS, imagenes)</li>
                <li>Templates HTML con Jinja2</li>
                <li>Configuracion lista para usar</li>
            </ul>
        </div>
        
        <div class="next-steps">
            <h2>Proximos Pasos</h2>
            <ol>
                <li>Edita los archivos en <code>{app_path}</code></li>
                <li>Agrega tu logica de negocio en <code>app.py</code></li>
                <li>Personaliza los templates en <code>templates/</code></li>
                <li>Añade estilos en <code>static/css/</code></li>
                <li>Inicia el servidor con el comando mostrado abajo</li>
            </ol>
        </div>
        
        <button class="btn" onclick="showMessage()">Pruébame!</button>
        <div id="message" style="margin-top: 20px; padding: 10px; background: #e7f3ff; border-radius: 4px; display: none;"></div>
    </div>
    
    <script src="{{ url_for('static', filename='js/app.js') }}"></script>
</body>
</html>'''
        
        # Create template file
        commands.append(f"echo '{template_content}' > {app_path}/templates/index.html")

        # Create framework-specific app.py
        if framework == 'microdot':
            app_py_content = get_microdot_app_content(app_name, framework, app_path, global_venv_python)
        elif framework == 'flask':
            app_py_content = get_flask_app_content(app_name, framework, app_path, global_venv_python)
        elif framework == 'fastapi':
            app_py_content = get_fastapi_app_content(app_name, framework, app_path, global_venv_python)
        else:
            app_py_content = get_microdot_app_content(app_name, framework, app_path, global_venv_python)
        
        commands.append(f"echo '{app_py_content}' > {app_path}/app.py")
        framework_packages = config.FRAMEWORK_PACKAGES.get(framework, [])
        if framework_packages:
            packages_str = " ".join(framework_packages)
            commands.append(f"{global_venv_pip} install -U {packages_str}")
        
        # Ejecutar comandos
        for cmd in commands:
            result = subprocess.run(
                [adb_bin, 'shell', cmd],
                capture_output=True, text=True, timeout=180
            )
            if result.returncode != 0:
                return json.dumps({
                    'success': False,
                    'error': f'Error en comando: {cmd}',
                    'details': (result.stderr or result.stdout)
                })
        
        # Crear archivo de configuración usando config
        config_content = f'''# App Configuration
APP_NAME = "{app_name}"
FRAMEWORK = "{framework}"
APP_PATH = "{app_path}"
PORT = {config.DEFAULT_APP_PORT}

# Global Environment
GLOBAL_VENV_PATH = "{config.GLOBAL_VENV_PATH}"
GLOBAL_VENV_PYTHON = "{config.GLOBAL_VENV_PYTHON}"

# Dependencies
REQUIRED_PACKAGES = {framework_packages}
'''
        
        config_cmd = f"echo '{config_content}' > {app_path}/config.py"
        subprocess.run([adb_bin, 'shell', config_cmd], timeout=10)
        
        return json.dumps({
            'success': True,
            'message': f'App creada para {app_name} (usando entorno global)',
            'app_path': app_path,
            'framework': framework,
            'global_venv': config.GLOBAL_VENV_PATH,
            'next_steps': [
                f'Crea tu app en {app_path}/app.py',
                f'Python: {global_venv_python}',
                f'Inicia el servidor: cd {app_path} && {global_venv_python} app.py'
            ]
        })
        
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })

@app.route('/api/devtools/list_apps', methods=['GET'])
def list_web_apps(request):
    """Listar apps web instaladas"""
    try:
        # Listar directorios en /home/phablet/Apps
        result = subprocess.run(
            ['adb', 'shell', 'ls -la /home/phablet/Apps/ 2>/dev/null || echo "No apps found"'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0 or "No apps found" in result.stdout:
            return json.dumps({
                'success': True,
                'apps': []
            })
        
        # Parsear salida para obtener apps
        apps = []
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if line.startswith('d') and '.' not in line.split()[-1]:  # Directorios que no empiezan con .
                app_name = line.split()[-1]
                
                # Global venv is shared (no per-app venv)
                venv_check = subprocess.run(
                    ['adb', 'shell', 'test -x /home/phablet/.ubtool/venv/bin/python && echo "yes" || echo "no"'],
                    capture_output=True, text=True, timeout=5
                )
                
                # Leer configuración si existe
                config_check = subprocess.run(
                    ['adb', 'shell', f'test -f /home/phablet/Apps/{app_name}/config.py && cat /home/phablet/Apps/{app_name}/config.py || echo ""'],
                    capture_output=True, text=True, timeout=5
                )
                
                config = {}
                if config_check.returncode == 0:
                    for line in config_check.stdout.strip().split('\n'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip().strip('"\'')
                
                apps.append({
                    'name': app_name,
                    'has_venv': venv_check.stdout.strip() == 'yes',
                    'config': config,
                    'path': f'/home/phablet/Apps/{app_name}',
                    'global_venv': '/home/phablet/.ubtool/venv'
                })
        
        return json.dumps({
            'success': True,
            'apps': apps
        })
        
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })

@app.route('/api/devtools/start_app', methods=['POST'])
def start_web_app(request):
    """Iniciar app web"""
    try:
        data = request.json or {}
        app_name = data.get('app_name', '').strip()
        
        if not app_name:
            return json.dumps({
                'success': False,
                'error': 'Nombre de app requerido'
            })
        
        # Verificar si la app existe
        check_cmd = f"test -d /home/phablet/Apps/{app_name}"
        check_result = subprocess.run(['adb', 'shell', check_cmd], timeout=5)
        
        if check_result.returncode != 0:
            return json.dumps({
                'success': False,
                'error': f'App {app_name} no encontrada'
            })
        
        # Iniciar app usando venv global
        start_cmd = f"cd /home/phablet/Apps/{app_name} && nohup /home/phablet/.ubtool/venv/bin/python app.py > app.log 2>&1 &"
        result = subprocess.run(['adb', 'shell', start_cmd], timeout=10)
        
        if result.returncode == 0:
            return json.dumps({
                'success': True,
                'message': f'App {app_name} iniciada',
                'access_url': f'http://localhost:8081'  # Esto debería ser dinámico
            })
        else:
            return json.dumps({
                'success': False,
                'error': 'Error al iniciar la app',
                'details': result.stderr
            })
            
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })

@app.route('/api/devtools/stop_app', methods=['POST'])
def stop_web_app(request):
    """Detener app web"""
    try:
        data = request.json or {}
        app_name = data.get('app_name', '').strip()
        
        if not app_name:
            return json.dumps({
                'success': False,
                'error': 'Nombre de app requerido'
            })
        
        # Detener app (matar proceso python)
        stop_cmd = f"pkill -f '/home/phablet/Apps/{app_name}.*app.py' || pkill -f 'app.py.*{app_name}'"
        result = subprocess.run(['adb', 'shell', stop_cmd], timeout=10)
        
        return json.dumps({
            'success': True,
            'message': f'App {app_name} detenida'
        })
        
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })

@app.route('/api/devtools/delete_app', methods=['POST'])
def delete_web_app(request):
    """Eliminar app web"""
    try:
        data = request.json or {}
        app_name = data.get('app_name', '').strip()
        
        if not app_name:
            return json.dumps({
                'success': False,
                'error': 'Nombre de app requerido'
            })
        
        # Detener app primero
        stop_cmd = f"pkill -f '/home/phablet/Apps/{app_name}.*app.py' || pkill -f 'app.py.*{app_name}'"
        subprocess.run(['adb', 'shell', stop_cmd], timeout=10)
        
        # Eliminar directorio de la app
        delete_cmd = f"rm -rf /home/phablet/Apps/{app_name}"
        result = subprocess.run(['adb', 'shell', delete_cmd], timeout=10)
        
        if result.returncode == 0:
            return json.dumps({
                'success': True,
                'message': f'App {app_name} eliminada correctamente'
            })
        else:
            return json.dumps({
                'success': False,
                'error': f'Error al eliminar app {app_name}'
            })
        
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })

@app.route('/api/devtools/prepare_deploy', methods=['POST'])
def prepare_app_for_deployment(request):
    """Preparar webapp para deployment con estructura completa y archivos necesarios"""
    try:
        data = request.json or {}
        app_name = data.get('app_name', '').strip()
        
        if not app_name:
            return json.dumps({
                'success': False,
                'error': 'Nombre de app requerido'
            })
        
        adb_bin = adb_manager.adb_path or 'adb'
        app_path = f"/home/phablet/Apps/{app_name}"
        deploy_path = f"/home/phablet/Apps/{app_name}_deploy"
        
        # Verificar que la app existe
        check_cmd = f"test -d {app_path}"
        check_result = subprocess.run([adb_bin, 'shell', check_cmd], timeout=5)
        if check_result.returncode != 0:
            return json.dumps({
                'success': False,
                'error': f'La app {app_name} no existe'
            })
        
        # Leer configuración de la app
        config_check = subprocess.run(
            [adb_bin, 'shell', f'cat {app_path}/config.py || echo ""'],
            capture_output=True, text=True, timeout=10
        )
        
        config = {}
        if config_check.returncode == 0:
            for line in config_check.stdout.strip().split('\n'):
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.split('=', 1)
                    config[key.strip()] = value.strip().strip('"\'')
        
        framework = config.get('FRAMEWORK', 'microdot')
        port = config.get('PORT', '8081')
        
        # Comandos para preparar estructura de deployment
        commands = [
            # Crear directorio de deployment
            f"rm -rf {deploy_path}",
            f"mkdir -p {deploy_path}",
            f"mkdir -p {deploy_path}/templates",
            f"mkdir -p {deploy_path}/static/css",
            f"mkdir -p {deploy_path}/static/js",
            f"mkdir -p {deploy_path}/static/images",
            
            # Copiar archivos existentes
            f"cp -r {app_path}/* {deploy_path}/ 2>/dev/null || true",
        ]
        
        # Crear requirements.txt
        requirements_content = f"""# Requirements for {app_name}
# Framework dependencies
{framework}==latest
jinja2==3.1.2

# Production server
gunicorn==21.2.0

# Utilities
click==8.1.7
"""
        if framework == 'flask':
            requirements_content = requirements_content.replace('flask==latest', 'flask==2.3.3')
        elif framework == 'fastapi':
            requirements_content = requirements_content.replace('fastapi==latest', 'fastapi==0.104.1')
            requirements_content = requirements_content.replace('gunicorn==21.2.0', 'uvicorn[standard]==0.24.0')
        elif framework == 'microdot':
            requirements_content = requirements_content.replace('microdot==latest', 'microdot==2.0.0')
        
        # Crear app.py mejorado con Click CLI
        app_py_content = f'''#!/usr/bin/env python3
"""
{app_name} - Web Application
Framework: {framework}
"""

import os
import sys
import click
from pathlib import Path

# Framework imports
{get_framework_imports(framework)}

# App configuration
BASE_DIR = Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

{get_app_code(framework, app_name)}

@click.group()
@click.version_option(version="1.0.0")
def cli():
    """{app_name} - Web Application CLI"""
    pass

@cli.command()
@click.option('--host', default='0.0.0.0', help='Host to bind to')
@click.option('--port', default={port}, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def run(host, port, debug):
    """Run the web application"""
    {get_run_code(framework, host, port, debug)}

@cli.command()
@click.option('--output', default='dist', help='Output directory for deployment')
def build(output):
    """Build the application for deployment"""
    click.echo(f"Building {app_name} for deployment...")
    
    # Create output directory
    output_dir = Path(output)
    output_dir.mkdir(exist_ok=True)
    
    # Copy application files
    import shutil
    shutil.copytree('templates', output_dir / 'templates', dirs_exist_ok=True)
    shutil.copytree('static', output_dir / 'static', dirs_exist_ok=True)
    shutil.copy('app.py', output_dir)
    shutil.copy('requirements.txt', output_dir)
    shutil.copy('config.py', output_dir)
    
    click.echo(f"✅ Build completed in {{output_dir}}")
    click.echo("Deploy with: python app.py run")

@cli.command()
def deploy():
    """Deploy preparation checklist"""
    click.echo("🚀 Deployment Checklist for {app_name}")
    click.echo()
    
    # Check requirements
    if Path('requirements.txt').exists():
        click.echo("✅ requirements.txt found")
    else:
        click.echo("❌ requirements.txt missing")
    
    # Check templates
    if Path('templates').exists():
        templates = list(Path('templates').glob('*.html'))
        click.echo(f"✅ {{len(templates)}} template(s) found")
    else:
        click.echo("❌ templates directory missing")
    
    # Check static files
    if Path('static').exists():
        click.echo("✅ static directory found")
    else:
        click.echo("❌ static directory missing")
    
    # Check app.py
    if Path('app.py').exists():
        click.echo("✅ app.py found")
    else:
        click.echo("❌ app.py missing")
    
    click.echo()
    click.echo("📋 Next steps:")
    click.echo("1. Run: pip install -r requirements.txt")
    click.echo("2. Run: python app.py run --host 0.0.0.0 --port {port}")
    click.echo("3. Access: http://localhost:{port}")

if __name__ == '__main__':
    cli()
'''
        
        # Crear Dockerfile
        dockerfile_content = f'''FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \\
    gcc \\
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE {port}

# Run the application
CMD ["python", "app.py", "run", "--host", "0.0.0.0", "--port", "{port}"]
'''
        
        # Crear docker-compose.yml
        docker_compose_content = f'''version: '3.8'

services:
  {app_name}:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - PYTHONPATH=/app
    restart: unless-stopped
    volumes:
      - ./logs:/app/logs
'''
        
        # Crear .dockerignore
        dockerignore_content = '''__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis
.venv
venv/
ENV/
env/
'''
        
        # Crear README.md para la app
        readme_content = f'''# {app_name}

Web application built with {framework}.

## Features

- Modern web framework ({framework})
- CLI interface with Click
- Docker support
- Production-ready structure

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py run

# Or with custom options
python app.py run --host 0.0.0.0 --port {port}
```

### Docker Deployment

```bash
# Build and run with Docker Compose
docker-compose up --build

# Or build manually
docker build -t {app_name} .
docker run -p {port}:{port} {app_name}
```

## CLI Commands

- `python app.py run` - Start the web server
- `python app.py build` - Build for deployment
- `python app.py deploy` - Show deployment checklist

## Project Structure

```
{app_name}/
├── app.py              # Main application
├── config.py           # Configuration
├── requirements.txt    # Python dependencies
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose setup
├── .dockerignore       # Docker ignore file
├── templates/         # HTML templates
├── static/           # Static files
│   ├── css/
│   ├── js/
│   └── images/
└── README.md         # This file
```

## Configuration

Edit `config.py` to modify application settings:

- `APP_NAME`: Application name
- `FRAMEWORK`: Web framework used
- `PORT`: Server port
- `REQUIRED_PACKAGES`: Python dependencies

## License

MIT License
'''
        
        # Ejecutar comandos de creación
        for cmd in commands:
            result = subprocess.run(
                [adb_bin, 'shell', cmd],
                capture_output=True, text=True, timeout=60
            )
            if result.returncode != 0:
                return json.dumps({
                    'success': False,
                    'error': f'Error en comando: {cmd}',
                    'details': result.stderr
                })
        
        # Escribir archivos usando base64 para evitar problemas con caracteres especiales
        import base64
        
        files_to_create = [
            ('requirements.txt', requirements_content),
            ('app.py', app_py_content),
            ('Dockerfile', dockerfile_content),
            ('docker-compose.yml', docker_compose_content),
            ('.dockerignore', dockerignore_content),
            ('README.md', readme_content)
        ]
        
        for filename, content in files_to_create:
            content_b64 = base64.b64encode(content.encode()).decode()
            write_cmd = f"echo '{content_b64}' | base64 -d > {deploy_path}/{filename}"
            result = subprocess.run([adb_bin, 'shell', write_cmd], timeout=30)
            if result.returncode != 0:
                return json.dumps({
                    'success': False,
                    'error': f'Error al crear {filename}',
                    'details': result.stderr
                })
        
        # Hacer ejecutable el app.py
        chmod_cmd = f"chmod +x {deploy_path}/app.py"
        subprocess.run([adb_bin, 'shell', chmod_cmd], timeout=10)
        
        return json.dumps({
            'success': True,
            'message': f'App {app_name} preparada para deployment',
            'deploy_path': deploy_path,
            'structure': {
                'app_py': 'Main application with Click CLI',
                'requirements': 'Python dependencies',
                'dockerfile': 'Docker configuration',
                'docker_compose': 'Docker Compose setup',
                'readme': 'Documentation',
                'templates': 'HTML templates directory',
                'static': 'Static files directory (css, js, images)'
            },
            'next_steps': [
                f'cd {deploy_path}',
                'pip install -r requirements.txt',
                'python app.py run',
                f'Access: http://localhost:{port}',
                'Or use: docker-compose up --build'
            ]
        })
        
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })

def get_framework_imports(framework):
    """Obtener imports según el framework"""
    imports = {
        'flask': 'from flask import Flask, render_template, request as flask_request',
        'microdot': 'from microdot import Microdot, send_file, Request as MicrodotRequest',
        'fastapi': 'from fastapi import FastAPI, Request as FastAPIRequest'
    }
    return imports.get(framework, '')

def get_app_code(framework, app_name):
    """Obtener código de la app según el framework"""
    if framework == 'flask':
        return f'''
app = Flask(__name__, template_folder=str(TEMPLATE_DIR), static_folder=str(STATIC_DIR))

@app.route('/')
def index():
    return render_template('index.html', app_name="{app_name}")

@app.route('/api/status')
def status():
    return {{"status": "running", "app": "{app_name}"}}
'''
    elif framework == 'microdot':
        return f'''
app = Microdot()

@app.route('/')
async def index(request):
    template_path = TEMPLATE_DIR / 'index.html'
    if template_path.exists():
        return send_file(str(template_path))
    return f"<h1>{app_name}</h1><p>App is running!</p>"

@app.route('/api/status')
async def status(request):
    return {{"status": "running", "app": "{app_name}"}}
'''
    elif framework == 'fastapi':
        return f'''
app = FastAPI()

@app.get('/')
async def index():
    return {{"message": "Welcome to {app_name}", "status": "running"}}

@app.get('/api/status')
async def status():
    return {{"status": "running", "app": "{app_name}"}}
'''
    return ''

def get_run_code(framework, host, port, debug):
    """Obtener código para correr la app según el framework"""
    if framework == 'flask':
        return f'''
app.run(host=host, port=port, debug=debug)
'''
    elif framework == 'microdot':
        return f'''
app.run(host=host, port=port, debug=debug)
'''
    elif framework == 'fastapi':
        return f'''
import uvicorn
uvicorn.run(app, host=host, port=port, debug=debug)
'''
    return ''

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

@app.route('/api/version/check')
async def check_version(request):
    """API: Verificar si hay actualizaciones disponibles"""
    # Initialize with default version to ensure it's always available
    current_version = "v1.4.0"
    
    try:
        import re
        import requests
        
        # Get current version from file
        try:
            with open('version.txt', 'r') as f:
                current_version = f.read().strip()
        except:
            pass
        
        # Get latest version from GitHub
        response = requests.get('https://api.github.com/repos/lukasgaleano/UBTool/releases/latest', timeout=5)
        if response.status_code == 200:
            latest_version = response.json().get('tag_name', 'v1.4.0')
            
            # Compare versions (simple string comparison for now)
            has_update = latest_version != current_version
            
            return {
                'success': True,
                'current_version': current_version,
                'latest_version': latest_version,
                'has_update': has_update,
                'download_url': f"https://github.com/lukasgaleano/UBTool/releases/tag/{latest_version}"
            }
        else:
            return {
                'success': False,
                'error': 'No se pudo verificar la versión',
                'current_version': current_version
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'current_version': current_version
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
        'error': result.get('error'),
        'return_code': result.get('return_code', 0)
    }

@app.route('/api/device/open_url', methods=['POST'])
async def open_url_on_device(request):
    """API: Abrir una URL en el navegador por defecto del dispositivo Ubuntu Touch."""
    try:
        if not adb_manager.is_available():
            return {'success': False, 'error': 'ADB no disponible'}

        devices = adb_manager.get_devices()
        if not devices:
            return {'success': False, 'error': 'No hay dispositivos conectados'}

        device_id = devices[0]['id']
        data = request.json or {}
        url = (data.get('url') or '').strip()
        if not url:
            return {'success': False, 'error': 'url requerida'}

        # Basic validation
        if not (url.startswith('http://') or url.startswith('https://')):
            return {'success': False, 'error': 'url inválida (debe empezar con http:// o https://)'}

        adb_bin = adb_manager.adb_path or 'adb'
        safe_url = url.replace("'", "'\\''")

        # Ubuntu Touch typically has url-dispatcher
        candidates = [
            f"url-dispatcher '{safe_url}'",
            f"xdg-open '{safe_url}'",
            f"/usr/bin/url-dispatcher '{safe_url}'",
        ]

        last = None
        for cmd in candidates:
            try:
                last = subprocess.run(
                    [adb_bin, '-s', device_id, 'shell', 'sh', '-c', cmd],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if last.returncode == 0:
                    return {
                        'success': True,
                        'message': 'URL abierta en el dispositivo',
                        'command': cmd
                    }
            except subprocess.TimeoutExpired:
                last = None
                continue

        err = ''
        if last is not None:
            err = (last.stderr or last.stdout or '').strip()

        return {
            'success': False,
            'error': err or 'No se pudo abrir la URL en el dispositivo',
            'tried': candidates
        }
    except Exception as e:
        return {'success': False, 'error': str(e)}

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
