from pydantic import BaseModel
from typing import List, Optional

class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[float] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    timestamp: float

class ConversationHistory(BaseModel):
    conversation_id: str
    messages: List[ChatMessage]

class StreamEvent(BaseModel):
    type: str
    content: Optional[str] = None
    conversation_id: Optional[str] = None
    tool_name: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None