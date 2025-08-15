import json
import time
from typing import List, Dict, Any, Iterator
from openai import OpenAI
from ..core.config import settings
from ..core.models import StreamEvent
from ..tools.tool_registry import ToolRegistry

class LLMService:
    def __init__(self, tool_registry: ToolRegistry):
        self.client = OpenAI(base_url=settings.OPENAI_BASE, api_key=settings.OPENAI_KEY)
        self.tool_registry = tool_registry
        self._conversations: Dict[str, List[Dict]] = {}
    
    def get_conversation(self, conv_id: str) -> List[Dict]:
        """Get or create conversation history"""
        if conv_id not in self._conversations:
            self._conversations[conv_id] = [
                {"role": "system", "content": "You can call the python and browser tools. Use %pip to install packages if needed."}
            ]
        return self._conversations[conv_id]
    
    def save_conversation(self, conv_id: str, messages: List[Dict]):
        """Save conversation history"""
        self._conversations[conv_id] = messages
    
    def delete_conversation(self, conv_id: str):
        """Delete conversation history"""
        self._conversations.pop(conv_id, None)
    
    def list_conversations(self) -> List[str]:
        """List all conversation IDs"""
        return list(self._conversations.keys())
    
    def chat_sync(self, conv_id: str, message: str) -> str:
        """Synchronous chat completion"""
        messages = self.get_conversation(conv_id).copy()
        messages.append({"role": "user", "content": message})
        
        # Initial LLM call
        resp = self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=messages,
            tools=self.tool_registry.get_tool_definitions(),
            tool_choice="auto",
            temperature=settings.TEMPERATURE
        )
        
        msg = resp.choices[0].message
        
        # If no tool calls, return immediately
        if not getattr(msg, "tool_calls", None):
            self.save_conversation(conv_id, messages + [{"role": "assistant", "content": msg.content}])
            return msg.content
        
        # Handle tool calls
        messages.append({
            "role": "assistant", 
            "tool_calls": msg.tool_calls, 
            "content": msg.content
        })
        
        # Execute all tool calls
        for call in msg.tool_calls:
            result = self.tool_registry.execute_tool(
                call.function.name, 
                json.loads(call.function.arguments or "{}"), 
                conv_id
            )
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.function.name,
                "content": result
            })
        
        # Get final response after tool execution
        final_resp = self.client.chat.completions.create(
            model=settings.MODEL_NAME,
            messages=messages,
            temperature=settings.TEMPERATURE
        )
        
        final_msg = final_resp.choices[0].message
        self.save_conversation(conv_id, messages + [{"role": "assistant", "content": final_msg.content}])
        return final_msg.content
    
    def chat_stream(self, conv_id: str, message: str) -> Iterator[StreamEvent]:
        """Streaming chat completion"""
        messages = self.get_conversation(conv_id).copy()
        messages.append({"role": "user", "content": message})
        
        # Send conversation ID first
        yield StreamEvent(type="conversation_id", conversation_id=conv_id)
        
        try:
            # Initial LLM call (streaming)
            resp = self.client.chat.completions.create(
                model=settings.MODEL_NAME,
                messages=messages,
                tools=self.tool_registry.get_tool_definitions(),
                tool_choice="auto",
                temperature=settings.TEMPERATURE,
                stream=True
            )
            
            accumulated_content = ""
            tool_calls_data = []
            
            for chunk in resp:
                delta = chunk.choices[0].delta
                
                # Handle content streaming
                if hasattr(delta, 'content') and delta.content:
                    accumulated_content += delta.content
                    yield StreamEvent(type="content", content=delta.content)
                
                # Handle tool calls
                if hasattr(delta, 'tool_calls') and delta.tool_calls:
                    for tool_call in delta.tool_calls:
                        if tool_call.index is not None:
                            # Ensure we have enough tool calls in our list
                            while len(tool_calls_data) <= tool_call.index:
                                tool_calls_data.append({
                                    "id": None, 
                                    "type": "function", 
                                    "function": {"name": "", "arguments": ""}
                                })
                            
                            current_tool_call = tool_calls_data[tool_call.index]
                            
                            if tool_call.id:
                                current_tool_call["id"] = tool_call.id
                            
                            if tool_call.function:
                                if tool_call.function.name:
                                    current_tool_call["function"]["name"] = tool_call.function.name
                                    yield StreamEvent(type="tool_start", tool_name=tool_call.function.name)
                                
                                if tool_call.function.arguments:
                                    current_tool_call["function"]["arguments"] += tool_call.function.arguments
            
            # If we have tool calls, execute them
            if tool_calls_data and any(tc["id"] for tc in tool_calls_data):
                yield StreamEvent(type="tools_executing")
                
                # Add assistant message with tool calls to conversation
                messages.append({
                    "role": "assistant",
                    "content": accumulated_content,
                    "tool_calls": tool_calls_data
                })
                
                # Execute each tool call
                for tool_call in tool_calls_data:
                    if tool_call["id"]:
                        yield StreamEvent(type="tool_executing", tool_name=tool_call['function']['name'])
                        
                        result = self.tool_registry.execute_tool(
                            tool_call["function"]["name"], 
                            json.loads(tool_call["function"]["arguments"] or "{}"), 
                            conv_id
                        )
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "name": tool_call["function"]["name"],
                            "content": result
                        })
                        
                        yield StreamEvent(
                            type="tool_result", 
                            tool_name=tool_call['function']['name'], 
                            result=result[:200] + '...' if len(result) > 200 else result
                        )
                
                # Get final streaming response after tool execution
                yield StreamEvent(type="final_response_start")
                
                final_resp = self.client.chat.completions.create(
                    model=settings.MODEL_NAME,
                    messages=messages,
                    temperature=settings.TEMPERATURE,
                    stream=True
                )
                
                final_content = ""
                for chunk in final_resp:
                    delta = chunk.choices[0].delta
                    if hasattr(delta, 'content') and delta.content:
                        final_content += delta.content
                        yield StreamEvent(type="content", content=delta.content)
                
                # Save final conversation state
                self.save_conversation(conv_id, messages + [{"role": "assistant", "content": final_content}])
            else:
                # No tool calls, save the direct response
                self.save_conversation(conv_id, messages + [{"role": "assistant", "content": accumulated_content}])
            
            yield StreamEvent(type="complete")
            
        except Exception as e:
            yield StreamEvent(type="error", error=str(e))