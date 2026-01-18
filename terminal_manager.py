#!/usr/bin/env python3
"""
Terminal Manager for UBTool
Manages interactive shell sessions with ADB devices
"""

import re
import asyncio
import json
import subprocess
import threading
import time
from typing import Dict, Optional, Callable
import ptyprocess

# ANSI escape code patterns
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


class TerminalSession:
    """Manages a single terminal session"""
    
    def __init__(self, session_id: str, adb_path: str, device_id: str):
        self.session_id = session_id
        self.adb_path = adb_path
        self.device_id = device_id
        self.process: Optional[ptyprocess.PtyProcessUnicode] = None
        self.active = False
        self.callbacks: Dict[str, Callable] = {}
        self.output_buffer = []
        
    def start(self):
        """Start the terminal session"""
        try:
            # Start ADB shell process
            cmd = [self.adb_path, '-s', self.device_id, 'shell']
            self.process = ptyprocess.PtyProcessUnicode.spawn(cmd)
            self.active = True
            
            # Start output monitoring thread
            threading.Thread(target=self._monitor_output, daemon=True).start()
            
            return True
        except Exception as e:
            print(f"Error starting terminal session: {e}")
            return False
    
    def _monitor_output(self):
        """Monitor terminal output in background thread"""
        while self.active and self.process:
            try:
                if self.process.isalive():
                    # Read available output without blocking
                    try:
                        # Use read_non_blocking to avoid hanging
                        if hasattr(self.process, 'read_non_blocking'):
                            output = self.process.read_non_blocking()
                        else:
                            # Fallback to read with small size
                            output = self.process.read(1024)
                        
                        if output and output.strip():
                            self._handle_output(output)
                    except (ptyprocess.PtyProcessError, EOFError):
                        # Process died or EOF
                        self._handle_output("\r\n[Proceso terminado]\r\n")
                        break
                    except Exception:
                        # Other read errors, continue
                        pass
                else:
                    # Process is no longer alive
                    self.active = False
                    self._handle_output("\r\n[Conexión cerrada]\r\n")
                    break
                    
                time.sleep(0.05)  # Slightly longer delay to prevent CPU spinning
                
            except Exception as e:
                print(f"Error monitoring output: {e}")
                break
        
        self.active = False
    
    def _handle_output(self, output: str):
        """Handle terminal output"""
        # Clean ANSI escape codes for better web display
        clean_output = self._clean_ansi_codes(output)
        self.output_buffer.append(clean_output)
        
        # Notify callbacks
        for callback in self.callbacks.values():
            try:
                callback(self.session_id, clean_output)
            except Exception as e:
                print(f"Error in callback: {e}")
    
    def _clean_ansi_codes(self, text: str) -> str:
        """Remove ANSI escape codes from text"""
        # Remove ANSI escape sequences using regex
        clean_text = ANSI_ESCAPE_PATTERN.sub('', text)
        
        # Remove specific problematic sequences
        problematic_sequences = [
            '\x1b]0;',      # Window title sequences
            '\x07',          # Bell character
            '\x1b[?2004h',   # Bracketed paste mode
            '\x1b[?2004l',   # Bracketed paste mode off
            '\x1b[01;32m',   # Green bold
            '\x1b[01;34m',   # Blue bold  
            '\x1b[00m',      # Reset
            '\x1b[0m',       # Reset
            '\x1b[34m',      # Blue
            '\x1b[32m',      # Green
            '\x1b[31m',      # Red
            '\x1b[33m',      # Yellow
            '\x1b[35m',      # Magenta
            '\x1b[36m',      # Cyan
            '\x1b[01;31m',   # Red bold
            '\x1b[01;33m',   # Yellow bold
            '\x1b[01;35m',   # Magenta bold
            '\x1b[01;36m',   # Cyan bold
            '\x1b[01;34m',   # Blue bold
            '\x1b[01;32m',   # Green bold
            '\x1b[m',        # Reset
            '\x1b[K',        # Clear line
            '\x1b[H',        # Home
            '\x1b[2J',       # Clear screen
            '\x1b[J',        # Clear to end of screen
            '\x1b[0G',       # Move to beginning of line
        ]
        
        for seq in problematic_sequences:
            clean_text = clean_text.replace(seq, '')
        
        # Clean up any remaining control characters
        clean_text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', clean_text)
        
        # Replace multiple spaces with single space (but preserve newlines)
        lines = clean_text.split('\n')
        cleaned_lines = []
        for line in lines:
            # Remove extra spaces but keep the structure
            cleaned_line = re.sub(r' +', ' ', line.strip())
            cleaned_lines.append(cleaned_line)
        
        return '\n'.join(cleaned_lines)
    
    def write_input(self, data: str):
        """Write input to terminal"""
        if self.process and self.active:
            try:
                # Ensure data ends with newline if it doesn't already
                if not data.endswith('\n'):
                    data += '\n'
                
                # Write the command
                self.process.write(data)
                
                # Force flush to ensure command is sent
                if hasattr(self.process, 'flush'):
                    self.process.flush()
                
                return True
            except Exception as e:
                print(f"Error writing to terminal: {e}")
                return False
        return False
    
    def resize(self, rows: int, cols: int):
        """Resize terminal"""
        if self.process and self.active:
            try:
                self.process.setwinsize(rows, cols)
                return True
            except Exception as e:
                print(f"Error resizing terminal: {e}")
                return False
        return False
    
    def add_callback(self, callback_id: str, callback: Callable):
        """Add output callback"""
        self.callbacks[callback_id] = callback
    
    def remove_callback(self, callback_id: str):
        """Remove output callback"""
        if callback_id in self.callbacks:
            del self.callbacks[callback_id]
    
    def get_buffer(self) -> str:
        """Get output buffer"""
        return ''.join(self.output_buffer)
    
    def clear_buffer(self):
        """Clear output buffer"""
        self.output_buffer.clear()
    
    def close(self):
        """Close terminal session"""
        self.active = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait()
            except:
                try:
                    self.process.kill()
                except:
                    pass
        self.process = None


class TerminalManager:
    """Manages multiple terminal sessions"""
    
    def __init__(self, adb_manager):
        self.adb_manager = adb_manager
        self.sessions: Dict[str, TerminalSession] = {}
        self.session_counter = 0
        
    def create_session(self, device_id: str = None) -> Optional[str]:
        """Create a new terminal session"""
        if not self.adb_manager.is_available():
            return None
        
        # Get device if not specified
        if not device_id:
            devices = self.adb_manager.get_devices()
            if not devices:
                return None
            device_id = devices[0]['id']
        
        # Generate session ID
        self.session_counter += 1
        session_id = f"session_{self.session_counter}_{int(time.time())}"
        
        # Create session
        session = TerminalSession(session_id, self.adb_manager.adb_path, device_id)
        
        if session.start():
            self.sessions[session_id] = session
            return session_id
        else:
            return None
    
    def get_session(self, session_id: str) -> Optional[TerminalSession]:
        """Get terminal session by ID"""
        return self.sessions.get(session_id)
    
    def write_to_session(self, session_id: str, data: str) -> bool:
        """Write data to terminal session"""
        session = self.get_session(session_id)
        if session:
            return session.write_input(data)
        return False
    
    def resize_session(self, session_id: str, rows: int, cols: int) -> bool:
        """Resize terminal session"""
        session = self.get_session(session_id)
        if session:
            return session.resize(rows, cols)
        return False
    
    def close_session(self, session_id: str):
        """Close terminal session"""
        session = self.get_session(session_id)
        if session:
            session.close()
            if session_id in self.sessions:
                del self.sessions[session_id]
    
    def get_active_sessions(self) -> Dict[str, dict]:
        """Get list of active sessions"""
        active_sessions = {}
        for session_id, session in self.sessions.items():
            if session.active:
                active_sessions[session_id] = {
                    'id': session_id,
                    'device_id': session.device_id,
                    'active': session.active,
                    'buffer_length': len(session.output_buffer)
                }
        return active_sessions
    
    def cleanup_inactive_sessions(self):
        """Clean up inactive sessions"""
        inactive_sessions = []
        for session_id, session in self.sessions.items():
            if not session.active:
                inactive_sessions.append(session_id)
        
        for session_id in inactive_sessions:
            self.close_session(session_id)
    
    def close_all_sessions(self):
        """Close all terminal sessions"""
        for session_id in list(self.sessions.keys()):
            self.close_session(session_id)
