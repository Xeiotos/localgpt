import json
import requests
from ddgs import DDGS
from bs4 import BeautifulSoup

class BrowserTool:
    @property
    def definition(self):
        return {
            "type": "function",
            "function": {
                "name": "browser",
                "description": "Search or fetch web pages.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["search", "open"]},
                        "query": {"type": "string"},
                        "url": {"type": "string", "format": "uri"},
                        "limit": {"type": "integer", "default": 5}
                    },
                    "required": ["action"]
                }
            }
        }
    
    def execute(self, conv_id: str, args: dict) -> str:
        if args["action"] == "search":
            with DDGS() as ddg:
                res = ddg.text(args.get("query", ""), max_results=int(args.get("limit", 5)))
            return json.dumps(res[:int(args.get("limit", 5))])
        
        elif args["action"] == "open":
            r = requests.get(args["url"], timeout=15)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)[:2000]
        
        return "unknown browser action"