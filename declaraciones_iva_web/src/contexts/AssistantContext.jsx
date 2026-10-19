import React, { createContext, useContext, useState, useCallback, useEffect } from 'react';

const AssistantContext = createContext();

export const useAssistant = () => useContext(AssistantContext);

export const AssistantProvider = ({ children }) => {
  const [isActive, setIsActive] = useState(false);
  const [message, setMessage] = useState('');
  const [options, setOptions] = useState(null);
  
  // Custom message queue for multiple messages
  const [messageQueue, setMessageQueue] = useState([]);

  const say = useCallback((text, ops = null) => {
    setMessage(text);
    setOptions(ops);
    setIsActive(true);
  }, []);

  const dismiss = useCallback(() => {
    setIsActive(false);
    setMessage('');
    setOptions(null);
    setMessageQueue([]);
  }, []);

  const enqueueMessages = useCallback((messagesArray) => {
    if (messagesArray.length === 0) return;
    
    // Si solo es 1 mensaje, dilo directamente
    if (messagesArray.length === 1) {
      say(messagesArray[0].text, messagesArray[0].options);
      return;
    }
    
    // Join messages into a single text block with newlines to avoid clicking "next" 100 times
    const combinedText = messagesArray.map(m => (m.type === 'error' ? '❌ ' : '✅ ') + m.text).join('\n\n');
    say(combinedText);
  }, [say]);

  return (
    <AssistantContext.Provider value={{ isActive, message, options, say, dismiss, enqueueMessages }}>
      {children}
    </AssistantContext.Provider>
  );
};
