import json
import time
import uuid
from websocket import create_connection
from .docker_service import DockerService

class JupyterService:
    def __init__(self, docker_service: DockerService):
        self.docker_service = docker_service
    
    def _jupyter_execute(self, ws_url: str, code: str, timeout: int = 30) -> str:
        """Execute code in Jupyter kernel via websocket"""
        session = uuid.uuid4().hex
        msg_id = uuid.uuid4().hex
        content = {
            "code": code, 
            "silent": False, 
            "store_history": True, 
            "allow_stdin": False, 
            "stop_on_error": True
        }
        header = {
            "msg_id": msg_id, 
            "username": "user", 
            "session": session, 
            "date": "", 
            "msg_type": "execute_request", 
            "version": "5.3"
        }
        msg = {
            "header": header, 
            "parent_header": {}, 
            "metadata": {}, 
            "content": content
        }
        
        ws = create_connection(ws_url, timeout=timeout)
        ws.send(json.dumps(msg))
        
        stdout, stderr = [], []
        result = None
        idle = False
        t0 = time.time()
        
        while time.time() - t0 < timeout:
            raw = ws.recv()
            m = json.loads(raw)
            mtype = m.get("msg_type") or m.get("msg", "")
            c = m.get("content", {})
            
            if mtype in ("stream",):
                (stdout if c.get("name") == "stdout" else stderr).append(c.get("text", ""))
            elif mtype == "execute_result":
                data = c.get("data", {})
                if "text/plain" in data:
                    result = data["text/plain"]
            elif mtype == "error":
                stderr.append("\n".join(c.get("traceback", [])))
            elif mtype == "status" and c.get("execution_state") == "idle":
                idle = True
                break
        
        ws.close()
        
        if not idle and not result and not stdout and not stderr:
            return "[python error] timeout"
        if stderr:
            return "[python error]\n" + "".join(stderr)
        return (result or "") + "".join(stdout)
    
    def execute_python(self, conv_id: str, code: str) -> str:
        """Execute Python code for a conversation"""
        s = self.docker_service.ensure_kernel(conv_id)
        s["last_used"] = time.time()
        return self._jupyter_execute(s["ws_url"], code)