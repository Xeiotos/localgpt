from ..services.jupyter_service import JupyterService

class PythonTool:
    def __init__(self, jupyter_service: JupyterService):
        self.jupyter_service = jupyter_service
    
    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": "python",
                "description": "Execute Python code in a stateful Jupyter kernel. Use %pip to install packages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"}
                    },
                    "required": ["code"]
                }
            }
        }
    
    def execute(self, conv_id: str, args: dict) -> str:
        return self.jupyter_service.execute_python(conv_id, args["code"])