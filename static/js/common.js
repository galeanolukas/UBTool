// Common functions for UBTool - included in all pages

// Sidebar functionality
let sidebarTimeout;
let isSidebarOpen = false;

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebar-overlay');
    const toggleBtn = document.getElementById('sidebar-toggle');
    
    // Check if elements exist before trying to manipulate them
    if (!sidebar) {
        console.warn('Sidebar element not found');
        return;
    }
    
    if (isSidebarOpen) {
        sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('active');
        if (toggleBtn) toggleBtn.classList.remove('active');
        isSidebarOpen = false;
        clearSidebarTimeout();
    } else {
        sidebar.classList.add('open');
        if (overlay) overlay.classList.add('active');
        if (toggleBtn) toggleBtn.classList.add('active');
        isSidebarOpen = true;
        startSidebarTimeout();
    }
}

function startSidebarTimeout() {
    clearSidebarTimeout();
    sidebarTimeout = setTimeout(() => {
        if (isSidebarOpen) {
            toggleSidebar();
        }
    }, 5000); // Auto-hide after 5 seconds
}

function clearSidebarTimeout() {
    if (sidebarTimeout) {
        clearTimeout(sidebarTimeout);
        sidebarTimeout = null;
    }
}

// Initialize sidebar event listeners
document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    if (sidebar) {
        sidebar.addEventListener('mouseenter', () => {
            if (isSidebarOpen) {
                clearSidebarTimeout();
            }
        });
        
        sidebar.addEventListener('mouseleave', () => {
            if (isSidebarOpen) {
                startSidebarTimeout();
            }
        });
    }
});

// File Manager Functions
function getFileIcon(name, isDir) {
    if (isDir) {
        return `📁 ${name}`;
    }
    
    const ext = (name.split('.').pop() || '').toLowerCase();
    const videoFormats = ['mp4', 'webm', 'ogg', 'mov', 'mkv', 'avi', '3gp', 'flv', 'wmv', 'm4v', 'wav', 'weba', 'mpg', 'mpeg', 'm4a'];
    const imageFormats = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico'];
    
    if (videoFormats.includes(ext)) {
        return `📹 ${name}`;
    } else if (imageFormats.includes(ext)) {
        return `🖼️ ${name}`;
    } else {
        return `📄 ${name}`;
    }
}

async function openFile(path) {
    // Check if it's a video file first
    const ext = (path.split('.').pop() || '').toLowerCase();
    const videoFormats = ['mp4', 'webm', 'ogg', 'mov', 'mkv', 'avi', '3gp', 'flv', 'wmv', 'm4v', 'wav', 'weba'];
    
    if (videoFormats.includes(ext)) {
        // Open video directly in player
        openBinaryViewer(path);
        return;
    }
    
    // Check if it's an image file
    const imageFormats = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico'];
    if (imageFormats.includes(ext)) {
        // Open image directly in viewer
        openBinaryViewer(path);
        return;
    }
    
    // For other files, try to open as text first
    try {
        const res = await fetch(`/api/files/text?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        if (data.success) {
            openTextEditor(path, data.content || '', data.mime || 'text/plain');
            return;
        }
    } catch (e) {
        // Fall back to viewer
    }

    openBinaryViewer(path);
}

function openBinaryViewer(path) {
    const modal = document.createElement('div');
    modal.id = 'file-viewer-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1100;
    `;

    const url = `/api/files/raw?path=${encodeURIComponent(path)}`;
    const ext = (path.split('.').pop() || '').toLowerCase();
    const isImage = ['png','jpg','jpeg','gif','bmp','webp','svg','ico'].includes(ext);
    const isVideo = ['mp4','webm','ogg','mov','mkv','avi','3gp','flv','wmv','m4v','wav','weba','mpg','mpeg','m4a'].includes(ext);

    let body = '';
    if (isImage) {
        body = `<img src="${url}" style="max-width: 100%; max-height: 70vh; border-radius: 8px;" />`;
    } else if (isVideo) {
        body = `
            <video src="${url}" controls style="max-width: 100%; max-height: 70vh; border-radius: 8px;" autoplay>
                Tu navegador no soporta el elemento de video.
            </video>
            <div style="text-align: center; margin-top: 1rem;">
                <p style="color: var(--ub-gray); font-size: 0.9rem;">
                    📹 Reproduciendo: <code style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px;">${path}</code>
                </p>
            </div>
        `;
    } else {
        body = `<div style="opacity:0.9; margin-bottom: 1rem;">Archivo: <code>${path}</code></div>
                <a class="btn-ub" href="${url}" target="_blank" rel="noopener">Abrir/Descargar</a>`;
    }

    modal.innerHTML = `
        <div style="background: var(--ub-dark); border: 2px solid var(--ub-orange); border-radius: 12px; padding: 1rem; max-width: 1000px; width: 95%; max-height: 90vh; overflow: auto;">
            <div style="display:flex; justify-content: space-between; align-items:center; gap: 0.5rem; margin-bottom: 0.75rem;">
                <h3 style="color: var(--ub-orange); margin: 0;">
                    ${isImage ? '🖼️ Imagen' : isVideo ? '📹 Reproductor de Video' : '👁️ Viewer'}
                </h3>
                <button onclick="closeFileViewer()" style="background: none; border: none; color: var(--ub-light); font-size: 1.5rem; cursor: pointer;">&times;</button>
            </div>
            <div style="text-align: center;">
                ${body}
            </div>
            ${isVideo ? `
            <div style="display: flex; justify-content: center; gap: 1rem; margin-top: 1rem;">
                <a href="${url}" download="${path.split('/').pop()}" class="btn-ub" style="background: var(--ub-orange); color: white; text-decoration: none; padding: 0.5rem 1rem; border-radius: 6px;">
                    💾 Descargar Video
                </a>
                <button onclick="closeFileViewer()" class="btn-ub" style="background: rgba(255,255,255,0.1); color: var(--ub-light); border: 1px solid var(--ub-orange); padding: 0.5rem 1rem; border-radius: 6px;">
                    Cerrar
                </button>
            </div>
            ` : ''}
        </div>
    `;

    document.body.appendChild(modal);
    
    // Close on escape key
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            closeFileViewer();
            document.removeEventListener('keydown', handleEscape);
        }
    };
    document.addEventListener('keydown', handleEscape);
    
    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            closeFileViewer();
            document.removeEventListener('keydown', handleEscape);
        }
    });
}

function closeFileViewer() {
    const modal = document.getElementById('file-viewer-modal');
    if (modal) modal.remove();
}

function openTextEditor(path, content, mime) {
    const modal = document.createElement('div');
    modal.id = 'file-editor-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1100;
    `;

    modal.innerHTML = `
        <div style="background: var(--ub-dark); border: 2px solid var(--ub-orange); border-radius: 12px; padding: 1rem; max-width: 1000px; width: 95%; max-height: 90vh; overflow: hidden; display: flex; flex-direction: column;">
            <div style="display:flex; justify-content: space-between; align-items:center; gap: 0.5rem; margin-bottom: 0.75rem;">
                <h3 style="color: var(--ub-orange); margin: 0;">📝 Editor de Texto</h3>
                <button onclick="closeTextEditor()" style="background: none; border: none; color: var(--ub-light); font-size: 1.5rem; cursor: pointer;">&times;</button>
            </div>
            <div style="margin-bottom: 0.5rem;">
                <code style="color: var(--ub-gray); font-size: 0.9rem;">${path}</code>
            </div>
            <textarea id="file-editor-content" style="flex: 1; background: rgba(255,255,255,0.05); border: 1px solid var(--ub-gray); color: var(--ub-light); padding: 1rem; border-radius: 6px; font-family: 'Courier New', monospace; font-size: 14px; resize: none; white-space: pre; overflow: auto;">${content}</textarea>
            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 1rem;">
                <div style="color: var(--ub-gray); font-size: 0.9rem;">
                    MIME: ${mime}
                </div>
                <div style="display: flex; gap: 0.5rem;">
                    <button onclick="saveFile('${path}')" class="btn-ub" style="background: var(--ub-orange); color: white; padding: 0.5rem 1rem; border-radius: 6px;">
                        💾 Guardar
                    </button>
                    <button onclick="closeTextEditor()" class="btn-ub" style="background: rgba(255,255,255,0.1); color: var(--ub-light); border: 1px solid var(--ub-orange); padding: 0.5rem 1rem; border-radius: 6px;">
                        Cerrar
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    
    // Close on escape key
    const handleEscape = (e) => {
        if (e.key === 'Escape') {
            closeTextEditor();
            document.removeEventListener('keydown', handleEscape);
        }
    };
    document.addEventListener('keydown', handleEscape);
}

function closeTextEditor() {
    const modal = document.getElementById('file-editor-modal');
    if (modal) modal.remove();
}

async function saveFile(path) {
    const content = document.getElementById('file-editor-content').value;
    try {
        const response = await fetch('/api/files/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path, content })
        });
        const data = await response.json();
        if (data.success) {
            alert('✅ Archivo guardado exitosamente');
        } else {
            alert(`❌ Error al guardar: ${data.error}`);
        }
    } catch (error) {
        alert(`❌ Error de conexión: ${error.message}`);
    }
}

// Terminal and File Manager Functions
function openTerminal() {
    createRealTerminalModal();
}

function openFileManager() {
    const modal = document.createElement('div');
    modal.id = 'file-manager-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.9);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;

    modal.innerHTML = `
        <div style="background: var(--ub-dark); border: 2px solid var(--ub-orange); border-radius: 12px; padding: 1rem; max-width: 900px; width: 95%; max-height: 90vh; overflow: hidden;">
            <div style="display:flex; justify-content: space-between; align-items:center; gap: 0.5rem; margin-bottom: 0.75rem;">
                <h3 style="color: var(--ub-orange); margin: 0;">📁 File Manager</h3>
                <button onclick="closeFileManager()" style="background: none; border: none; color: var(--ub-light); font-size: 1.5rem; cursor: pointer;">&times;</button>
            </div>
            <div style="display:flex; gap: 0.5rem; align-items:center; margin-bottom: 0.75rem;">
                <button class="btn-ub" style="padding: 0.5rem 0.75rem;" onclick="fmGoUp()">⬆️</button>
                <input id="fm-path" type="text" style="flex:1; background: rgba(255,255,255,0.1); border: 1px solid var(--ub-gray); color: var(--ub-light); padding: 0.6rem; border-radius: 6px;" />
                <button class="btn-ub" style="padding: 0.5rem 0.75rem;" onclick="fmGoToPath()">Ir</button>
            </div>
            <div id="fm-status" style="margin-bottom: 0.5rem; opacity: 0.9;"></div>
            <div id="fm-list" style="background: rgba(0,0,0,0.35); border: 1px solid var(--ub-gray); border-radius: 8px; padding: 0.5rem; height: 60vh; overflow-y: auto; font-family: 'Ubuntu', 'Arial', sans-serif;"></div>
        </div>
    `;

    document.body.appendChild(modal);
    document.getElementById('fm-path').value = fmCurrentPath;
    loadFileManagerPath(fmCurrentPath);
}

// File Manager Variables and Functions
let fmCurrentPath = '/home/phablet';

function closeFileManager() {
    const modal = document.getElementById('file-manager-modal');
    if (modal) modal.remove();
}

function fmGoUp() {
    if (!fmCurrentPath || fmCurrentPath === '/') {
        loadFileManagerPath('/');
        return;
    }
    const parent = fmCurrentPath.replace(/\/+$/, '').split('/').slice(0, -1).join('/') || '/';
    loadFileManagerPath(parent);
}

function fmGoToPath() {
    const p = (document.getElementById('fm-path').value || '').trim();
    if (!p) return;
    loadFileManagerPath(p);
}

async function loadFileManagerPath(path) {
    const status = document.getElementById('fm-status');
    const list = document.getElementById('fm-list');
    const pathInput = document.getElementById('fm-path');
    if (!status || !list || !pathInput) return;

    status.innerHTML = '<span class="loading-spinner"></span> Cargando...';
    list.innerHTML = '';

    try {
        const url = `/api/files/list?path=${encodeURIComponent(path)}`;
        const response = await fetch(url);
        const data = await response.json();

        if (!data.success) {
            status.innerHTML = `❌ ${data.error || 'Error al listar'}`;
            return;
        }

        const payload = data.data;
        fmCurrentPath = payload.path || path;
        pathInput.value = fmCurrentPath;
        status.textContent = fmCurrentPath;

        const entries = payload.entries || [];
        if (!entries.length) {
            list.innerHTML = '<div style="opacity:0.8; padding: 0.5rem;">(vacío)</div>';
            return;
        }

        let html = '';
        for (const e of entries) {
            const name = e.name || '';
            const isDir = !!e.is_dir;
            const size = e.size_human || '';
            const rowStyle = 'display:flex; justify-content: space-between; gap: 0.75rem; padding: 0.5rem; border-radius: 6px; cursor: pointer;';
            
            let left;
            if (isDir) {
                left = `📁 ${name}`;
            } else {
                const ext = (name.split('.').pop() || '').toLowerCase();
                const videoFormats = ['mp4', 'webm', 'ogg', 'mov', 'mkv', 'avi', '3gp', 'flv', 'wmv', 'm4v', 'wav', 'weba', 'mpg', 'mpeg', 'm4a'];
                const imageFormats = ['png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'svg', 'ico'];
                
                if (videoFormats.includes(ext)) {
                    left = `📹 ${name}`;
                } else if (imageFormats.includes(ext)) {
                    left = `🖼️ ${name}`;
                } else {
                    left = `📄 ${name}`;
                }
            }
            
            html += `
                <div style="${rowStyle}" onmouseover="this.style.background='rgba(233,84,32,0.10)'" onmouseout="this.style.background='transparent'" onclick="fmEntryClick(${isDir ? 'true' : 'false'}, '${encodeURIComponent(name)}')">
                    <div style="overflow:hidden; text-overflow: ellipsis; white-space: nowrap;">${left}</div>
                    <div style="opacity:0.8; white-space: nowrap;">${isDir ? '' : size}</div>
                </div>
            `;
        }
        list.innerHTML = html;
    } catch (e) {
        status.innerHTML = `❌ Error: ${e.message}`;
    }
}

function fmEntryClick(isDir, encodedName) {
    const name = decodeURIComponent(encodedName || '');
    if (!name) return;
    if (isDir) {
        const base = (fmCurrentPath || '/').replace(/\/+$/, '');
        const next = (base === '' || base === '/') ? `/${name}` : `${base}/${name}`;
        loadFileManagerPath(next);
    } else {
        const base = (fmCurrentPath || '/').replace(/\/+$/, '');
        const fullPath = (base === '' || base === '/') ? `/${name}` : `${base}/${name}`;
        openFile(fullPath);
    }
}

// Terminal Functions
let terminalSessionId = null;
let terminalInterval = null;

function createRealTerminalModal() {
    const modal = document.createElement('div');
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;

    modal.innerHTML = `
        <div style="background: var(--ub-dark); border: 2px solid var(--ub-orange); border-radius: 12px; padding: 1rem; max-width: 800px; width: 95%; max-height: 90vh; overflow: hidden;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="color: var(--ub-orange); margin: 0;">🖥️ Terminal Ubuntu Touch - Shell del Dispositivo</h3>
                <div style="display:flex; gap: 0.5rem; align-items:center;">
                    <button onclick="openRootPrompt()" class="btn-ub" style="padding: 0.5rem 0.75rem;">Root</button>
                    <button onclick="closeTerminal()" style="background: none; border: none; color: var(--ub-light); font-size: 1.5rem; cursor: pointer;">&times;</button>
                </div>
            </div>
            <div style="background: rgba(233, 84, 32, 0.1); border: 1px solid var(--ub-orange); border-radius: 8px; padding: 0.75rem; margin-bottom: 1rem; font-size: 0.9rem;">
                <strong>Comandos útiles:</strong> 
                <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">ls -la</code> • 
                <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">ps aux</code> • 
                <code style="background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px;">getprop</code>
            </div>
            <div id="terminal-output" style="background: #000; color: #0f0; padding: 1rem; border-radius: 8px; height: 400px; overflow-y: auto; font-family: 'Courier New', monospace; font-size: 14px; line-height: 1.4; margin-bottom: 1rem; white-space: pre-wrap;"></div>
            <div style="display: flex; gap: 0.5rem;">
                <input type="text" id="terminal-command" placeholder="Escribe un comando del shell del dispositivo..." style="flex: 1; background: rgba(255,255,255,0.1); border: 1px solid var(--ub-gray); color: var(--ub-light); padding: 0.75rem; border-radius: 4px; font-family: 'Courier New', monospace;">
                <button onclick="sendTerminalCommand()" class="btn-ub">Enviar</button>
            </div>
            <div style="margin-top: 0.5rem; font-size: 0.8rem; opacity: 0.7;">
                Estado: <span id="device-status-terminal">Verificando...</span> | 
                Sesión: <span id="session-id-terminal">No iniciada</span>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // Initialize terminal
    initializeTerminal();
    
    // Focus on input
    setTimeout(() => {
        document.getElementById('terminal-command').focus();
    }, 100);

    // Handle Enter key
    document.getElementById('terminal-command').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendTerminalCommand();
        }
    });
}

async function initializeTerminal() {
    try {
        // Create terminal session
        const response = await fetch('/api/terminal/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({})
        });
        
        const data = await response.json();
        
        if (data.success) {
            terminalSessionId = data.session_id;
            document.getElementById('device-status-terminal').textContent = 'Conectado al dispositivo';
            document.getElementById('session-id-terminal').textContent = data.session_id.substring(0, 12) + '...';
            
            // Start polling for output
            terminalInterval = setInterval(pollTerminalOutput, 500);
            
            // Start with empty output
            const output = document.getElementById('terminal-output');
            output.textContent = '';
        } else {
            document.getElementById('device-status-terminal').textContent = 'Error: ' + data.error;
            document.getElementById('session-id-terminal').textContent = 'N/A';
            document.getElementById('terminal-output').textContent = 'Error al conectar terminal: ' + data.error;
        }
    } catch (error) {
        console.error('Error initializing terminal:', error);
        document.getElementById('device-status-terminal').textContent = 'Error de conexión';
        document.getElementById('session-id-terminal').textContent = 'N/A';
        document.getElementById('terminal-output').textContent = 'Error al inicializar terminal';
    }
}

async function sendTerminalCommand() {
    const commandInput = document.getElementById('terminal-command');
    const output = document.getElementById('terminal-output');
    
    if (!commandInput || !terminalSessionId) return;

    const command = commandInput.value.trim();
    if (!command) return;
    
    // Send command to terminal (without \r\n since manager adds it)
    try {
        const response = await fetch(`/api/terminal/${terminalSessionId}/write`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ input: command })
        });
        
        const data = await response.json();
        
        if (!data.success) {
            output.textContent += `Error: ${data.error}\r\n`;
        }
    } catch (error) {
        output.textContent += `Error de conexión: ${error.message}\r\n`;
    }

    // Clear input and scroll to bottom
    commandInput.value = '';
    output.scrollTop = output.scrollHeight;
}

async function pollTerminalOutput() {
    if (!terminalSessionId) return;
    
    try {
        const response = await fetch(`/api/terminal/${terminalSessionId}/output`);
        const data = await response.json();
        
        if (data.success && data.output) {
            const output = document.getElementById('terminal-output');
            let chunk = data.output;

            // Strip terminal control sequences (ANSI/OSC) that can show up as "0;user@host"
            // OSC: ESC ] ... BEL or ESC \
            chunk = chunk.replace(/\x1b\][\s\S]*?(?:\x07|\x1b\\)/g, '');
            // CSI: ESC [ ... letter
            chunk = chunk.replace(/\x1b\[[0-9;?]*[ -/]*[@-~]/g, '');
            // Fallback: sometimes title text leaks without the ESC prefix
            chunk = chunk.replace(/(^|\r?\n)0;[^\r\n]*?(?=(\r?\n|$))/g, '$1');

            // Simplify prompt: user@host:/path$ -> user$
            // Also handles root@host:/path# -> root#
            chunk = chunk.replace(/([a-zA-Z0-9_-]+)@[^\s:]+:[^\r\n$#]*([\$#])/g, '$1$2');

            output.textContent += chunk;
            output.scrollTop = output.scrollHeight;
            
            // Update status if session became inactive
            if (!data.active) {
                document.getElementById('device-status-terminal').textContent = 'Desconectado';
                clearInterval(terminalInterval);
                terminalInterval = null;
            }
        }
    } catch (error) {
        console.error('Error polling terminal:', error);
    }
}

function closeTerminal() {
    if (terminalInterval) {
        clearInterval(terminalInterval);
        terminalInterval = null;
    }
    
    if (terminalSessionId) {
        // Close terminal session
        fetch(`/api/terminal/${terminalSessionId}/close`, {
            method: 'POST'
        }).catch(console.error);
        terminalSessionId = null;
    }
    
    // Remove modal
    const modal = document.querySelector('div[style*="position: fixed"]');
    if (modal) {
        modal.remove();
    }
}

function openRootPrompt() {
    if (!terminalSessionId) return;

    const existing = document.getElementById('root-prompt-modal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'root-prompt-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1100;
    `;

    modal.innerHTML = `
        <div style="background: var(--ub-dark); border: 2px solid var(--ub-orange); border-radius: 12px; padding: 2rem; max-width: 400px; width: 90%;">
            <h3 style="color: var(--ub-orange); margin: 0 0 1rem 0;">🔑 Acceso Root</h3>
            <p style="color: var(--ub-light); margin-bottom: 1.5rem;">Ingresa la contraseña de root para obtener privilegios de administrador en el terminal.</p>
            <input type="password" id="root-password" placeholder="Contraseña root..." style="width: 100%; background: rgba(255,255,255,0.1); border: 1px solid var(--ub-gray); color: var(--ub-light); padding: 0.75rem; border-radius: 6px; margin-bottom: 1rem;">
            <div style="display: flex; gap: 1rem;">
                <button onclick="sendRootCommand()" class="btn-ub" style="flex: 1; background: var(--ub-orange); color: white;">Enviar</button>
                <button onclick="closeRootPrompt()" class="btn-ub" style="flex: 1; background: rgba(255,255,255,0.1); color: var(--ub-light); border: 1px solid var(--ub-orange);">Cancelar</button>
            </div>
        </div>
    `;

    document.body.appendChild(modal);
    
    // Focus on password input
    setTimeout(() => {
        document.getElementById('root-password').focus();
    }, 100);

    // Handle Enter key
    document.getElementById('root-password').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendRootCommand();
        }
    });
}

async function sendRootCommand() {
    const password = document.getElementById('root-password').value.trim();
    if (!password) return;

    try {
        const response = await fetch(`/api/terminal/${terminalSessionId}/write`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ input: `su -c 'echo "${password}" | sudo -S su'` })
        });
        
        const data = await response.json();
        if (data.success) {
            closeRootPrompt();
        }
    } catch (error) {
        console.error('Error sending root command:', error);
    }
}

function closeRootPrompt() {
    const modal = document.getElementById('root-prompt-modal');
    if (modal) modal.remove();
}

// Web App Creation Modal
function createWebAppModal() {
    // Check if modal already exists
    const existingModal = document.getElementById('webapp-create-modal');
    if (existingModal) {
        existingModal.remove();
    }

    const modal = document.createElement('div');
    modal.id = 'webapp-create-modal';
    modal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
    `;

    modal.innerHTML = `
        <div style="background: var(--ub-dark); border: 2px solid var(--ub-orange); border-radius: 12px; padding: 2rem; max-width: 600px; width: 90%; max-height: 90vh; overflow-y: auto;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
                <h3 style="color: var(--ub-orange); margin: 0;" data-i18n="webapps.create.title">🚀 Crear Nueva WebApp</h3>
                <button onclick="closeWebAppModal()" style="background: none; border: none; color: var(--ub-light); font-size: 1.5rem; cursor: pointer;">&times;</button>
            </div>
            
            <form id="webapp-form" onsubmit="createWebApp(event)">
                <div style="margin-bottom: 1.5rem;">
                    <label style="display: block; margin-bottom: 0.5rem; color: var(--ub-light); font-weight: 500;" data-i18n="webapps.create.name">
                        Nombre de la App:
                    </label>
                    <input 
                        type="text" 
                        id="webapp-name" 
                        data-i18n-placeholder="webapps.create.name_ph"
                        placeholder="mi_app" 
                        required
                        pattern="[a-zA-Z][a-zA-Z0-9_-]*"
                        title="Debe comenzar con una letra y solo puede contener letras, números, guiones y guiones bajos"
                        style="width: 100%; background: rgba(255,255,255,0.1); border: 1px solid var(--ub-gray); color: var(--ub-light); padding: 0.75rem; border-radius: 6px; font-family: inherit;"
                    />
                    <small style="color: var(--ub-gray); font-size: 0.8rem; margin-top: 0.25rem; display: block;" data-i18n="webapps.create.name_hint">
                        Ej: mi_app, blog-todo, api_rest
                    </small>
                </div>
                
                <div style="margin-bottom: 1.5rem;">
                    <label style="display: block; margin-bottom: 0.5rem; color: var(--ub-light); font-weight: 500;" data-i18n="webapps.create.framework">
                        Framework/Servidor:
                    </label>
                    <select 
                        id="webapp-framework" 
                        required
                        style="width: 100%; background: rgba(255,255,255,0.1); border: 1px solid var(--ub-gray); color: var(--ub-light); padding: 0.75rem; border-radius: 6px; font-family: inherit;"
                    >
                        <option value="" data-i18n="webapps.create.framework_ph">Selecciona un framework...</option>
                        <optgroup label="Frameworks Ligeros (Recomendado)">
                            <option value="microdot">🚀 Microdot (Recomendado para UT)</option>
                            <option value="flask">🌶️ Flask</option>
                            <option value="fastapi">⚡ FastAPI</option>
                        </optgroup>
                        <optgroup label="Frameworks Completos">
                            <option value="django">🎸 Django</option>
                            <option value="bottle">🍾 Bottle</option>
                        </optgroup>
                        <optgroup label="Servidores Estáticos">
                            <option value="http-server">📁 Servidor HTTP Estático</option>
                            <option value="nodejs">🟢 Node.js Express</option>
                            <option value="react">⚛️ React</option>
                            <option value="vue">💚 Vue.js</option>
                        </optgroup>
                    </select>
                    <small style="color: var(--ub-gray); font-size: 0.8rem; margin-top: 0.25rem; display: block;" data-i18n="webapps.create.framework_hint">
                        Microdot es optimizado para Ubuntu Touch
                    </small>
                </div>
                
                <div style="margin-bottom: 1.5rem;">
                    <label style="display: block; margin-bottom: 0.5rem; color: var(--ub-light); font-weight: 500;" data-i18n="webapps.create.icon.title">
                        🎨 Icono de la App (opcional):
                    </label>
                    <input 
                        type="file" 
                        id="webapp-icon" 
                        accept="image/*"
                        style="width: 100%; background: rgba(255,255,255,0.1); border: 1px solid var(--ub-gray); color: var(--ub-light); padding: 0.75rem; border-radius: 6px; font-family: inherit;"
                        onchange="previewIcon(this)"
                    />
                    <small style="color: var(--ub-gray); font-size: 0.8rem; margin-top: 0.25rem; display: block;" data-i18n="webapps.create.icon.hint">
                        Formatos: PNG, JPG, SVG. Se redimensionará automáticamente a 64x64px
                    </small>
                    <div id="icon-preview" style="margin-top: 0.5rem; text-align: center; min-height: 80px; display: flex; align-items: center; justify-content: center;">
                        <div style="color: var(--ub-gray); font-size: 0.9rem;" data-i18n="webapps.create.icon.no_selection">No hay icono seleccionado</div>
                    </div>
                </div>
                
                <div style="margin-bottom: 1.5rem;">
                    <div style="background: rgba(233,84,32,0.1); border: 1px solid var(--ub-orange); border-radius: 8px; padding: 1rem;">
                        <h5 style="color: var(--ub-orange); margin: 0 0 0.5rem 0; font-size: 0.9rem;">🌍 Entorno Virtual Global</h5>
                        <p style="margin: 0; color: var(--ub-light); font-size: 0.85rem; line-height: 1.4;">
                            Esta app usará el entorno virtual global compartido configurado en UBTool, optimizando el uso de recursos y dependencias.
                        </p>
                    </div>
                </div>
                
                <div id="webapp-create-status" style="margin-bottom: 1rem; min-height: 1.5rem;"></div>
                
                <div style="display: flex; gap: 1rem;">
                    <button 
                        type="submit" 
                        id="create-webapp-btn"
                        data-i18n="webapps.create.submit"
                        style="flex: 1; background: var(--ub-orange); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 6px; cursor: pointer; font-weight: bold; transition: all 0.3s ease;"
                    >
                        🚀 Crear WebApp
                    </button>
                    <button 
                        type="button" 
                        onclick="closeWebAppModal()"
                        data-i18n="webapps.create.cancel"
                        style="flex: 1; background: rgba(255,255,255,0.1); color: var(--ub-light); border: 1px solid var(--ub-orange); padding: 0.75rem 1.5rem; border-radius: 6px; cursor: pointer; transition: all 0.3s ease;"
                    >
                        Cancelar
                    </button>
                </div>
            </form>
        </div>
    `;

    document.body.appendChild(modal);
    
    // Focus on name input
    setTimeout(() => {
        document.getElementById('webapp-name').focus();
    }, 100);
}

function previewIcon(input) {
    const preview = document.getElementById('icon-preview');
    if (!preview) return;
    
    const file = input.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            preview.innerHTML = `
                <img src="${e.target.result}" style="max-width: 64px; max-height: 64px; border-radius: 8px; border: 2px solid var(--ub-orange);" />
                <div style="margin-top: 0.5rem; color: var(--ub-light); font-size: 0.8rem;">
                    ${file.name} (${(file.size / 1024).toFixed(1)} KB)
                </div>
            `;
        };
        reader.readAsDataURL(file);
    } else {
        const currentLang = getCurrentLanguage ? getCurrentLanguage() : 'es';
        const noIconText = UBTOOL_I18N && UBTOOL_I18N[currentLang] ? 
            UBTOOL_I18N[currentLang]['webapps.create.icon.no_selection'] : 
            'No hay icono seleccionado';
        preview.innerHTML = `<div style="color: var(--ub-gray); font-size: 0.9rem;">${noIconText}</div>`;
    }
}

function closeWebAppModal() {
    const modal = document.getElementById('webapp-create-modal');
    if (modal) {
        modal.remove();
    }
}

async function createWebApp(event) {
    event.preventDefault();
    
    const name = document.getElementById('webapp-name').value.trim();
    const framework = document.getElementById('webapp-framework').value;
    const iconInput = document.getElementById('webapp-icon');
    const statusDiv = document.getElementById('webapp-create-status');
    const submitBtn = document.getElementById('create-webapp-btn');
    
    if (!name || !framework) {
        statusDiv.innerHTML = `<p style="color: #f44336;">❌ Por favor completa todos los campos requeridos</p>`;
        return;
    }
    
    // Disable button and show loading
    submitBtn.disabled = true;
    submitBtn.textContent = '⏳ Creando...';
    statusDiv.innerHTML = '<p style="color: var(--ub-orange);">🔄 Creando aplicación web...</p>';
    
    try {
        // Use FormData to support file upload
        const formData = new FormData();
        formData.append('app_name', name);
        formData.append('framework', framework);
        
        // Add icon file if selected
        if (iconInput.files && iconInput.files[0]) {
            formData.append('icon', iconInput.files[0]);
        }
        
        const response = await fetch('/api/devtools/create_env', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            statusDiv.innerHTML = `
                <div style="background: rgba(76,175,80,0.1); border: 1px solid #4CAF50; border-radius: 6px; padding: 1rem; margin-bottom: 1rem;">
                    <h4 style="color: #4CAF50; margin: 0 0 0.5rem 0;">✅ ${data.message}</h4>
                    <p style="margin: 0; color: var(--ub-light); font-size: 0.9rem;">
                        <strong>Ruta:</strong> ${data.app_path || 'N/A'}<br>
                        <strong>Framework:</strong> ${data.framework || 'N/A'}<br>
                        ${data.global_venv ? `<strong>Entorno Global:</strong> ${data.global_venv}<br>` : ''}
                        ${data.next_steps ? `<strong>Siguientes pasos:</strong><br>${data.next_steps.join('<br>')}` : ''}
                    </p>
                </div>
            `;
            
            // Reset form
            document.getElementById('webapp-form').reset();
            submitBtn.textContent = '✅ Creado Exitosamente';
            submitBtn.style.background = '#4CAF50';
            
            // Auto-close modal after 5 seconds (longer to show next steps)
            setTimeout(() => {
                closeWebAppModal();
                // If we're on the apps page, refresh the list
                if (window.location.pathname === '/apps') {
                    refreshAppsList();
                }
            }, 5000);
            
        } else {
            statusDiv.innerHTML = `<p style="color: #f44336;">❌ Error: ${data.error}</p>`;
            submitBtn.disabled = false;
            submitBtn.textContent = '🚀 Crear WebApp';
        }
    } catch (error) {
        statusDiv.innerHTML = `<p style="color: #f44336;">❌ Error de conexión: ${error.message}</p>`;
        submitBtn.disabled = false;
        submitBtn.textContent = '🚀 Crear WebApp';
    }
}
