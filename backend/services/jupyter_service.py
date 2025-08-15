import json
import time
import uuid
from websocket import create_connection
from .jupyter_gateway_service import JupyterGatewayService

class JupyterService:
    def __init__(self, jupyter_gateway_service: JupyterGatewayService):
        self.jupyter_gateway_service = jupyter_gateway_service
    
    def _jupyter_execute(self, ws_url: str, session_id: str, code: str, timeout: int = 120) -> str:
        """Execute code in Jupyter kernel via fresh websocket connection"""
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
            "session": session_id, 
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
        
        ws = create_connection(ws_url, timeout=30)
        
        try:
            # Send our execution request
            ws.send(json.dumps(msg))
            
            stdout, stderr = [], []
            result = None
            idle = False
            t0 = time.time()
            
            while time.time() - t0 < timeout:
                try:
                    raw = ws.recv()
                    m = json.loads(raw)
                    mtype = m.get("msg_type") or m.get("msg", "")
                    c = m.get("content", {})
                    
                    # Only process messages for our request
                    if m.get("parent_header", {}).get("msg_id") == msg_id:
                        if mtype in ("stream",):
                            (stdout if c.get("name") == "stdout" else stderr).append(c.get("text", ""))
                        elif mtype == "execute_result":
                            data = c.get("data", {})
                            if "text/plain" in data:
                                result = data["text/plain"]
                        elif mtype == "error":
                            stderr.append("\n".join(c.get("traceback", [])))
                        elif mtype == "status" and c.get("execution_state") == "idle":
                            # This idle status is for our request - we're done
                            idle = True
                            break
                except Exception as e:
                    break
            
        finally:
            ws.close()
        
        if not idle and not result and not stdout and not stderr:
            return "[python error] timeout"
        if stderr:
            return "[python error]\n" + "".join(stderr)
        return (result or "") + "".join(stdout)
    
    def execute_python(self, conv_id: str, code: str) -> str:
        """Execute Python code for a conversation"""
        kernel_info = self.jupyter_gateway_service.ensure_kernel(conv_id)
        kernel_info["last_used"] = time.time()
        return self._jupyter_execute(kernel_info["ws_url"], kernel_info["session_id"], code)