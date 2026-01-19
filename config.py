# UBTool Configuration File
# This file contains global settings for UBTool

# Global Virtual Environment Configuration
GLOBAL_VENV_PATH = "/home/phablet/.ubtool/venv"
GLOBAL_VENV_PYTHON = f"{GLOBAL_VENV_PATH}/bin/python"
GLOBAL_VENV_PIP = f"{GLOBAL_VENV_PATH}/bin/pip"

# Default App Configuration
DEFAULT_APP_PORT = 8081
APPS_BASE_PATH = "/home/phablet/Apps"

# Framework-specific default packages
FRAMEWORK_PACKAGES = {
    "microdot": ["microdot", "jinja2"],
    "flask": ["flask", "gunicorn", "jinja2"],
    "fastapi": ["fastapi", "uvicorn", "jinja2"],
    "django": ["django", "gunicorn"],
    "bottle": ["bottle"],
    "http-server": [],  # No additional packages needed
    "nodejs": [],  # Handled separately
    "react": [],  # Handled separately
    "vue": []  # Handled separately
}

# Development Environment Settings
DEV_ENV_AUTO_PREPARE = True
DEV_ENV_CHECK_TOOLS = ["python3", "pip", "virtualenv"]

# Server Configuration
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 8080
