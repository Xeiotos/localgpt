import React, { useState, useEffect } from 'react';
import {
  MainContainer,
  ChatContainer,
  MessageList,
  Message,
  MessageInput,
  TypingIndicator,
} from '@chatscope/chat-ui-kit-react';
import '@chatscope/chat-ui-kit-styles/dist/default/styles.min.css';
import './App.css';

const API_BASE = process.env.REACT_APP_API_BASE || 'http://localhost:8000';

function App() {
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId, setConversationId] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const handleSendMessage = async (message) => {
    const newUserMessage = {
      message,
      direction: 'outgoing',
      sender: 'user',
      sentTime: new Date().toLocaleTimeString(),
    };

    setMessages(prevMessages => [...prevMessages, newUserMessage]);
    setIsTyping(true);
    setIsStreaming(true);

    // Add a placeholder message for the assistant response
    const assistantMessageId = Date.now();
    const initialAssistantMessage = {
      message: '',
      direction: 'incoming',
      sender: 'assistant',
      sentTime: new Date().toLocaleTimeString(),
      id: assistantMessageId,
      isStreaming: true,
    };

    setMessages(prevMessages => [...prevMessages, initialAssistantMessage]);

    try {
      const response = await fetch(`${API_BASE}/api/chat/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let accumulatedContent = '';
      let toolStatus = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              switch (data.type) {
                case 'conversation_id':
                  setConversationId(data.conversation_id);
                  break;
                
                case 'content':
                  accumulatedContent += data.content;
                  setMessages(prevMessages => 
                    prevMessages.map(msg => 
                      msg.id === assistantMessageId 
                        ? { ...msg, message: accumulatedContent + (toolStatus ? `\n\n_${toolStatus}_` : '') }
                        : msg
                    )
                  );
                  break;

                case 'tool_start':
                  toolStatus = `🔧 Starting ${data.tool_name}...`;
                  setMessages(prevMessages => 
                    prevMessages.map(msg => 
                      msg.id === assistantMessageId 
                        ? { ...msg, message: accumulatedContent + `\n\n_${toolStatus}_` }
                        : msg
                    )
                  );
                  break;

                case 'tools_executing':
                  toolStatus = '🔧 Executing tools...';
                  setMessages(prevMessages => 
                    prevMessages.map(msg => 
                      msg.id === assistantMessageId 
                        ? { ...msg, message: accumulatedContent + `\n\n_${toolStatus}_` }
                        : msg
                    )
                  );
                  break;

                case 'tool_executing':
                  toolStatus = `🔧 Running ${data.tool_name}...`;
                  setMessages(prevMessages => 
                    prevMessages.map(msg => 
                      msg.id === assistantMessageId 
                        ? { ...msg, message: accumulatedContent + `\n\n_${toolStatus}_` }
                        : msg
                    )
                  );
                  break;

                case 'tool_result':
                  toolStatus = `✅ ${data.tool_name}: ${data.result}`;
                  setMessages(prevMessages => 
                    prevMessages.map(msg => 
                      msg.id === assistantMessageId 
                        ? { ...msg, message: accumulatedContent + `\n\n_${toolStatus}_` }
                        : msg
                    )
                  );
                  break;

                case 'final_response_start':
                  toolStatus = '';
                  setMessages(prevMessages => 
                    prevMessages.map(msg => 
                      msg.id === assistantMessageId 
                        ? { ...msg, message: accumulatedContent }
                        : msg
                    )
                  );
                  break;

                case 'complete':
                  setMessages(prevMessages => 
                    prevMessages.map(msg => 
                      msg.id === assistantMessageId 
                        ? { ...msg, message: accumulatedContent, isStreaming: false }
                        : msg
                    )
                  );
                  setIsStreaming(false);
                  break;

                case 'error':
                  const errorMessage = {
                    message: `Error: ${data.error}`,
                    direction: 'incoming',
                    sender: 'system',
                    sentTime: new Date().toLocaleTimeString(),
                  };
                  setMessages(prevMessages => [...prevMessages.slice(0, -1), errorMessage]);
                  break;
              }
            } catch (e) {
              console.error('Error parsing SSE data:', e);
            }
          }
        }
      }
    } catch (error) {
      const errorMessage = {
        message: `Network Error: ${error.message}`,
        direction: 'incoming',
        sender: 'system',
        sentTime: new Date().toLocaleTimeString(),
      };
      setMessages(prevMessages => [...prevMessages.slice(0, -1), errorMessage]);
    }

    setIsTyping(false);
    setIsStreaming(false);
  };

  return (
    <div className="App">
      <div className="chat-header">
        <h1>LocalGPT Chat</h1>
        {conversationId && (
          <span className="conversation-id">ID: {conversationId}</span>
        )}
      </div>
      
      <MainContainer style={{ height: 'calc(100vh - 80px)' }}>
        <ChatContainer>
          <MessageList
            scrollBehavior="smooth"
            typingIndicator={
              isTyping ? (
                <TypingIndicator content="Assistant is thinking..." />
              ) : null
            }
          >
            {messages.map((message, i) => (
              <Message
                key={i}
                model={message}
                style={
                  message.sender === 'system'
                    ? { backgroundColor: '#ffebee' }
                    : {}
                }
                className={message.isStreaming ? 'streaming-message' : ''}
              />
            ))}
          </MessageList>
          <MessageInput
            placeholder={isStreaming ? "Please wait for the response to complete..." : "Type message here..."}
            onSend={handleSendMessage}
            attachButton={false}
            disabled={isStreaming}
          />
        </ChatContainer>
      </MainContainer>
    </div>
  );
}

export default App;
