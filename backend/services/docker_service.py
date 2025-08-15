import docker
import uuid
import time
import requests
from urllib.parse import urljoin
from typing import Dict, Tuple
from ..core.config import settings

class DockerService:
    def __init__(self):
        self.dcli = docker.from_env()
        self._sessions: Dict[str, Dict] = {}
    
    def _spawn_gateway(self) -> Tuple[str, str]:
        """Spawn a new Jupyter gateway container"""
        name = f"kg-{uuid.uuid4().hex[:12]}"
        c = self.dcli.containers.run(
            settings.IMAGE,
            detach=True,
            name=name,
            ports={f"{settings.JUPY_PORT}/tcp": None},
            command=None
        )
        c.reload()
        
        # Find mapped port
        port = self.dcli.api.port(c.id, settings.JUPY_PORT)[0]["HostPort"]
        base = f"http://127.0.0.1:{port}"
        
        # Wait for /api to be up
        for _ in range(50):
            try:
                requests.get(urljoin(base, "/api"), timeout=1)
                break
            except Exception:
                time.sleep(0.2)
        
        return c.id, base
    
    def ensure_kernel(self, conv_id: str) -> Dict:
        """Ensure a kernel exists for the conversation"""
        s = self._sessions.get(conv_id)
        if s:
            s["last_used"] = time.time()
            return s
        
        cid, base = self._spawn_gateway()
        
        # Create a kernel
        r = requests.post(
            urljoin(base, f"/api/kernels?token={settings.JUPY_TOKEN}"), 
            json={"name": "python3"}, 
            timeout=5
        )
        r.raise_for_status()
        kid = r.json()["id"]
        ws = f"{base.replace('http','ws')}/api/kernels/{kid}/channels?token={settings.JUPY_TOKEN}"
        
        s = {
            "container_id": cid, 
            "base_url": base, 
            "kernel_id": kid, 
            "ws_url": ws, 
            "last_used": time.time()
        }
        self._sessions[conv_id] = s
        return s
    
    def cleanup_session(self, conv_id: str):
        """Clean up a specific session"""
        if conv_id in self._sessions:
            try:
                self.dcli.containers.get(self._sessions[conv_id]["container_id"]).remove(force=True)
            except Exception:
                pass
            del self._sessions[conv_id]
    
    def gc_idle(self, ttl: int = None):
        """Garbage collect idle sessions"""
        if ttl is None:
            ttl = settings.SESSION_TTL
            
        now = time.time()
        dead = [k for k, v in self._sessions.items() if now - v["last_used"] > ttl]
        
        for k in dead:
            try:
                self.dcli.containers.get(self._sessions[k]["container_id"]).remove(force=True)
            except Exception:
                pass
            self._sessions.pop(k, None)
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self._sessions)