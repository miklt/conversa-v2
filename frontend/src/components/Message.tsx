import React from 'react';
import type { ChatMessage } from '../types';

interface MessageProps {
  message: ChatMessage;
}

export const Message: React.FC<MessageProps> = ({ message }) => {
  const isUser = message.sender === 'user';
  
  return (
    <div className={`message ${isUser ? 'message-user' : 'message-ai'}`}>
      <div className="message-header">
        <span className="message-sender">
          {isUser ? 'Usuário' : 'Estagios IA'}
        </span>
        <span className="message-time">
          {message.timestamp.toLocaleTimeString()}
        </span>
      </div>
      <div className="message-content">
        {message.content}
      </div>
    </div>
  );
};