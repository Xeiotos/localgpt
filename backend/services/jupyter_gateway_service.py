import time
import requests
from urllib.parse import urljoin
from typing import Dict
from ..core.config import settings

class JupyterGatewayService:
    def __init__(self):
        self.gateway_url = f"http://jupyter-gateway:{settings.JUPY_PORT}"
        self._kernels: Dict[str, Dict] = {}
    
    def ensure_kernel(self, conv_id: str) -> Dict:
        """Ensure a kernel exists for the conversation"""
        kernel_info = self._kernels.get(conv_id)
        if kernel_info:
            kernel_info["last_used"] = time.time()
            return kernel_info
        
        # Create a new kernel in the shared Jupyter Gateway
        try:
            r = requests.post(
                urljoin(self.gateway_url, f"/api/kernels?token={settings.JUPY_TOKEN}"), 
                json={"name": "python3"}, 
                timeout=10
            )
            r.raise_for_status()
            kernel_data = r.json()
            kid = kernel_data["id"]
            
            # Generate a consistent session ID for this conversation
            import uuid
            session_id = uuid.uuid4().hex
            
            ws_url = f"{self.gateway_url.replace('http','ws')}/api/kernels/{kid}/channels?token={settings.JUPY_TOKEN}&session={session_id}"
            
            kernel_info = {
                "kernel_id": kid, 
                "ws_url": ws_url, 
                "base_url": self.gateway_url,
                "session_id": session_id,
                "last_used": time.time()
            }
            self._kernels[conv_id] = kernel_info
            return kernel_info
            
        except Exception as e:
            raise Exception(f"Failed to create kernel for conversation {conv_id}: {e}")
    
    def cleanup_session(self, conv_id: str):
        """Clean up a specific kernel"""
        if conv_id in self._kernels:
            kernel_info = self._kernels[conv_id]
            try:
                # Delete the kernel from Jupyter Gateway
                requests.delete(
                    urljoin(self.gateway_url, f"/api/kernels/{kernel_info['kernel_id']}?token={settings.JUPY_TOKEN}"),
                    timeout=5
                )
            except Exception:
                pass
            del self._kernels[conv_id]
    
    def gc_idle(self, ttl: int = None):
        """Garbage collect idle kernels"""
        if ttl is None:
            ttl = settings.JUPYTER_SESSION_TTL
            
        now = time.time()
        dead = [k for k, v in self._kernels.items() if now - v["last_used"] > ttl]
        
        for conv_id in dead:
            self.cleanup_session(conv_id)
    
    def get_session_count(self) -> int:
        """Get number of active kernels"""
        return len(self._kernels)