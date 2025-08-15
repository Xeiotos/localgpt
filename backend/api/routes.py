import json
import time
import uuid
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Iterator

from ..core.models import ChatRequest, ChatResponse, ConversationHistory, ChatMessage
from ..services.llm_service import LLMService

router = APIRouter()

def create_routes(llm_service: LLMService) -> APIRouter:
    
    def stream_chat_response(request: ChatRequest) -> Iterator[str]:
        """Generate SSE stream for chat response"""
        conv_id = request.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
        
        for event in llm_service.chat_stream(conv_id, request.message):
            event_data = event.model_dump(exclude_none=True)
            yield f"data: {json.dumps(event_data)}\n\n"
    
    @router.post("/chat/stream")
    async def chat_stream(request: ChatRequest):
        """Streaming chat endpoint"""
        return StreamingResponse(
            stream_chat_response(request),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/event-stream",
            }
        )
    
    @router.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        """Synchronous chat endpoint"""
        conv_id = request.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
        
        try:
            response = llm_service.chat_sync(conv_id, request.message)
            return ChatResponse(
                response=response,
                conversation_id=conv_id,
                timestamp=time.time()
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/conversations/{conv_id}", response_model=ConversationHistory)
    async def get_conversation(conv_id: str):
        """Get conversation history"""
        messages_raw = llm_service.get_conversation(conv_id)
        
        if not messages_raw:
            raise HTTPException(status_code=404, detail="Conversation not found")
        
        messages = [
            ChatMessage(role=msg["role"], content=msg.get("content", ""), timestamp=time.time())
            for msg in messages_raw
            if msg["role"] in ["user", "assistant"]
        ]
        
        return ConversationHistory(conversation_id=conv_id, messages=messages)
    
    @router.get("/conversations")
    async def list_conversations():
        """List all conversations"""
        return {"conversations": llm_service.list_conversations()}
    
    @router.delete("/conversations/{conv_id}")
    async def delete_conversation(conv_id: str):
        """Delete conversation"""
        llm_service.delete_conversation(conv_id)
        return {"message": "Conversation deleted"}
    
    @router.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {"status": "healthy", "timestamp": time.time()}
    
    return router