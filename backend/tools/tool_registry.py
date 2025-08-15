import json
from typing import Dict, List, Any
from .python_tool import PythonTool
from .browser_tool import BrowserTool
from ..services.jupyter_service import JupyterService

class ToolRegistry:
    def __init__(self, jupyter_service: JupyterService):
        self.tools = {
            "python": PythonTool(jupyter_service),
            "browser": BrowserTool()
        }
    
    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get OpenAI-compatible tool definitions"""
        return [tool.definition for tool in self.tools.values()]
    
    def execute_tool(self, name: str, args: dict, conv_id: str) -> str:
        """Execute a tool by name"""
        if name not in self.tools:
            return f"Unknown tool: {name}"
        
        try:
            return self.tools[name].execute(conv_id, args)
        except Exception as e:
            return f"Tool execution error: {str(e)}"
    
    def get_available_tools(self) -> List[str]:
        """Get list of available tool names"""
        return list(self.tools.keys())