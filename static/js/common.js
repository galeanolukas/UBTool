// Common functions for UBTool - included in all pages

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
        const response = await fetch('/api/devtools/create_env', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                app_name: name,
                framework: framework
            })
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
