// UBTool JavaScript - Ubuntu Touch Connection Tool

class UBTool {
    constructor() {
        this.apiBase = '/api';
        this.deviceStatus = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.checkDeviceStatus();
        // Auto-refresh device status every 30 seconds
        setInterval(() => this.checkDeviceStatus(), 30000);
    }

    bindEvents() {
        // Bind button events
        document.addEventListener('DOMContentLoaded', () => {
            const checkBtn = document.getElementById('check-device-btn');
            const infoBtn = document.getElementById('get-info-btn');
            const shellBtn = document.getElementById('shell-btn');
            const rebootBtn = document.getElementById('reboot-btn');

            if (checkBtn) checkBtn.addEventListener('click', () => this.checkDeviceStatus());
            if (infoBtn) infoBtn.addEventListener('click', () => this.getDeviceInfo());
            if (shellBtn) shellBtn.addEventListener('click', () => this.openShell());
            if (rebootBtn) rebootBtn.addEventListener('click', () => this.rebootDevice());
        });
    }

    async apiCall(endpoint, method = 'GET', data = null) {
        try {
            const options = {
                method: method,
                headers: {
                    'Content-Type': 'application/json',
                }
            };

            if (data && method !== 'GET') {
                options.body = JSON.stringify(data);
            }

            const response = await fetch(`${this.apiBase}${endpoint}`, options);
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            this.showAlert('Error de conexión con el servidor', 'error');
            return null;
        }
    }

    async checkDeviceStatus() {
        this.showLoading('device-status');
        
        const data = await this.apiCall('/device/status');
        
        if (data) {
            this.updateDeviceStatus(data);
        } else {
            this.updateDeviceStatus({ connected: false, error: true });
        }
    }

    updateDeviceStatus(status) {
        const statusElement = document.getElementById('device-status');
        const statusIndicator = document.querySelector('.status-indicator');
        
        if (!statusElement || !statusIndicator) return;

        if (status.connected) {
            statusElement.textContent = `Conectado - ${status.device || 'Dispositivo'}`;
            statusIndicator.className = 'status-indicator status-connected';
            this.deviceStatus = status;
        } else {
            statusElement.textContent = status.error ? 'Error de conexión' : 'No conectado';
            statusIndicator.className = 'status-indicator status-disconnected';
            this.deviceStatus = null;
        }
    }

    async getDeviceInfo() {
        if (!this.deviceStatus || !this.deviceStatus.connected) {
            this.showAlert('No hay dispositivo conectado', 'warning');
            return;
        }

        this.showLoading('device-info');
        
        const data = await this.apiCall('/device/info');
        
        if (data && data.info) {
            this.displayDeviceInfo(data.info);
        } else {
            document.getElementById('device-info').innerHTML = 
                '<span class="text-error">No se pudo obtener información</span>';
        }
    }

    displayDeviceInfo(info) {
        const infoElement = document.getElementById('device-info');
        if (!infoElement) return;

        infoElement.innerHTML = `
            <div class="device-info-grid">
                <div class="info-item">
                    <strong>Modelo:</strong> ${info.model || 'N/A'}
                </div>
                <div class="info-item">
                    <strong>Versión:</strong> ${info.version || 'N/A'}
                </div>
                <div class="info-item">
                    <strong>Serial:</strong> ${info.serial || 'N/A'}
                </div>
                <div class="info-item">
                    <strong>Batería:</strong> ${info.battery || 'N/A'}
                </div>
                <div class="info-item">
                    <strong>Almacenamiento:</strong> ${info.storage || 'N/A'}
                </div>
                <div class="info-item">
                    <strong>Red:</strong> ${info.network || 'N/A'}
                </div>
            </div>
        `;
    }

    async openShell() {
        if (!this.deviceStatus || !this.deviceStatus.connected) {
            this.showAlert('No hay dispositivo conectado', 'warning');
            return;
        }

        // Create shell modal
        this.createShellModal();
    }

    createShellModal() {
        const modal = document.createElement('div');
        modal.className = 'ub-modal';
        modal.innerHTML = `
            <div class="ub-modal-content">
                <div class="ub-modal-header">
                    <h3>Terminal ADB</h3>
                    <button class="ub-modal-close" onclick="this.closest('.ub-modal').remove()">&times;</button>
                </div>
                <div class="ub-modal-body">
                    <div class="terminal">
                        <div class="terminal-output" id="terminal-output"></div>
                        <div class="terminal-input">
                            <input type="text" id="terminal-command" placeholder="Escribe un comando..." />
                            <button onclick="ubtool.executeCommand()">Ejecutar</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.appendChild(modal);
        
        // Focus on input
        setTimeout(() => {
            document.getElementById('terminal-command').focus();
        }, 100);

        // Handle Enter key
        document.getElementById('terminal-command').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.executeCommand();
            }
        });
    }

    async executeCommand() {
        const commandInput = document.getElementById('terminal-command');
        const output = document.getElementById('terminal-output');
        
        if (!commandInput || !output) return;

        const command = commandInput.value.trim();
        if (!command) return;

        // Add command to output
        output.innerHTML += `<div class="terminal-command">$ ${command}</div>`;
        
        // Execute command
        const data = await this.apiCall('/device/shell', 'POST', { command });
        
        if (data) {
            output.innerHTML += `<div class="terminal-response">${data.output || data.error}</div>`;
        } else {
            output.innerHTML += `<div class="terminal-response error">Error ejecutando comando</div>`;
        }

        // Clear input and scroll to bottom
        commandInput.value = '';
        output.scrollTop = output.scrollHeight;
    }

    async rebootDevice() {
        if (!this.deviceStatus || !this.deviceStatus.connected) {
            this.showAlert('No hay dispositivo conectado', 'warning');
            return;
        }

        if (!confirm('¿Estás seguro de que quieres reiniciar el dispositivo?')) {
            return;
        }

        const data = await this.apiCall('/device/reboot', 'POST');
        
        if (data && data.success) {
            this.showAlert('Dispositivo reiniciándose...', 'success');
            // Check status again after a delay
            setTimeout(() => this.checkDeviceStatus(), 5000);
        } else {
            this.showAlert('Error al reiniciar dispositivo', 'error');
        }
    }

    showLoading(elementId) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = '<div class="ub-spinner"></div>';
        }
    }

    showAlert(message, type = 'info') {
        // Remove existing alerts
        const existingAlert = document.querySelector('.ub-alert');
        if (existingAlert) {
            existingAlert.remove();
        }

        const alert = document.createElement('div');
        alert.className = `ub-alert ub-alert-${type}`;
        alert.textContent = message;
        
        // Add to top of content
        const content = document.querySelector('.w3-content');
        if (content) {
            content.insertBefore(alert, content.firstChild);
        }

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }
}

// Initialize UBTool when page loads
const ubtool = new UBTool();

// Utility functions
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) {
        return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
        return `${hours}h ${minutes}m`;
    } else {
        return `${minutes}m`;
    }
}

// Export for global access
window.ubtool = ubtool;
window.formatBytes = formatBytes;
window.formatUptime = formatUptime;
