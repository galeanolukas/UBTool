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

        return json.dumps({
            'success': True,
            'message': 'Entorno listo (python3/pip/virtualenv)',
            'details': details
        })
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })

@app.route('/api/devtools/check', methods=['GET'])
def check_dev_tools():
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

@app.route('/api/devtools/create_env', methods=['POST'])
def create_virtual_env(request):
    """Crear entorno virtual para desarrollo de apps web"""
    try:
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
        
        # Comandos para crear entorno virtual
        app_path = f"/home/phablet/webapps/{app_name}"
        adb_bin = adb_manager.adb_path or 'adb'
        venv_dir = f"{app_path}/venv"
        venv_python = f"{venv_dir}/bin/python"
        venv_pip = f"{venv_dir}/bin/pip"
        commands = [
            f"mkdir -p {app_path}",
            f"python3 -m virtualenv {venv_dir}",
        ]
        
        # Instalar dependencias según framework
        if framework == 'flask':
            commands.extend([
                f"{venv_pip} install flask gunicorn",
                f"{venv_pip} install jinja2"
            ])
        elif framework == 'microdot':
            commands.extend([
                f"{venv_pip} install microdot",
                f"{venv_pip} install jinja2"
            ])
        elif framework == 'fastapi':
            commands.extend([
                f"{venv_pip} install fastapi uvicorn",
                f"{venv_pip} install jinja2"
            ])
        
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
        
        # Crear archivo de configuración
        config_content = f'''# App Configuration
APP_NAME = "{app_name}"
FRAMEWORK = "{framework}"
APP_PATH = "{app_path}"
PORT = 8081  # Puerto base, se puede incrementar

# Dependencies
if FRAMEWORK == "flask":
    REQUIRED_PACKAGES = ["flask", "gunicorn", "jinja2"]
elif FRAMEWORK == "microdot":
    REQUIRED_PACKAGES = ["microdot", "jinja2"]
elif FRAMEWORK == "fastapi":
    REQUIRED_PACKAGES = ["fastapi", "uvicorn", "jinja2"]
'''
        
        config_cmd = f"echo '{config_content}' > {app_path}/config.py"
        subprocess.run([adb_bin, 'shell', config_cmd], timeout=10)
        
        return json.dumps({
            'success': True,
            'message': f'Entorno virtual creado para {app_name}',
            'app_path': app_path,
            'framework': framework,
            'next_steps': [
                f'Crea tu app en {app_path}/app.py',
                'Activa el entorno: source venv/bin/activate',
                'Inicia el servidor: python app.py'
            ]
        })
        
    except Exception as e:
        return json.dumps({
            'success': False,
            'error': str(e)
        })

@app.route('/api/devtools/list_apps', methods=['GET'])
def list_web_apps():
    """Listar apps web instaladas"""
    try:
        # Listar directorios en /home/phablet/webapps
        result = subprocess.run(
            ['adb', 'shell', 'ls -la /home/phablet/webapps/ 2>/dev/null || echo "No apps found"'],
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
                
                # Verificar si tiene entorno virtual
                venv_check = subprocess.run(
                    ['adb', 'shell', f'test -d /home/phablet/webapps/{app_name}/venv && echo "yes" || echo "no"'],
                    capture_output=True, text=True, timeout=5
                )
                
                # Leer configuración si existe
                config_check = subprocess.run(
                    ['adb', 'shell', f'test -f /home/phablet/webapps/{app_name}/config.py && cat /home/phablet/webapps/{app_name}/config.py || echo ""'],
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
                    'path': f'/home/phablet/webapps/{app_name}'
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
def start_web_app():
    """Iniciar app web"""
    try:
        data = request.get_json()
        app_name = data.get('app_name', '').strip()
        
        if not app_name:
            return json.dumps({
                'success': False,
                'error': 'Nombre de app requerido'
            })
        
        # Verificar si la app existe
        check_cmd = f"test -d /home/phablet/webapps/{app_name}"
        check_result = subprocess.run(['adb', 'shell', check_cmd], timeout=5)
        
        if check_result.returncode != 0:
            return json.dumps({
                'success': False,
                'error': f'App {app_name} no encontrada'
            })
        
        # Iniciar app
        start_cmd = f"cd /home/phablet/webapps/{app_name} && source venv/bin/activate && nohup python app.py > app.log 2>&1 &"
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
def stop_web_app():
    """Detener app web"""
    try:
        data = request.get_json()
        app_name = data.get('app_name', '').strip()
        
        if not app_name:
            return json.dumps({
                'success': False,
                'error': 'Nombre de app requerido'
            })
        
        # Detener app (matar proceso python)
        stop_cmd = f"pkill -f 'python.*{app_name}'"
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
