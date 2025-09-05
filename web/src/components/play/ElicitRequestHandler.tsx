import { useState } from 'react';

interface ElicitRequestHandlerProps {
  varName: string;
  maxLen: number;
  onSubmit: (text: string) => void;
}

export default function ElicitRequestHandler({ varName, maxLen, onSubmit }: ElicitRequestHandlerProps) {
  const [inputValue, setInputValue] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = () => {
    if (!submitted && inputValue.trim()) {
      onSubmit(inputValue);
      setSubmitted(true);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  if (submitted) {
    return (
      <div style={{ 
        marginBottom: '15px', 
        padding: '10px', 
        backgroundColor: '#e8f5e9', 
        borderRadius: '5px',
        border: '1px solid #4CAF50'
      }}>
        <strong>Input for {varName}:</strong> {inputValue}
      </div>
    );
  }

  return (
    <div style={{ 
      marginBottom: '15px', 
      padding: '15px', 
      backgroundColor: '#fff3cd', 
      borderRadius: '5px',
      border: '1px solid #ffc107'
    }}>
      <div style={{ marginBottom: '10px' }}>
        <strong>Input requested for variable: {varName}</strong>
        <span style={{ marginLeft: '10px', fontSize: '12px', color: '#666' }}>
          (max {maxLen} tokens)
        </span>
      </div>
      <div style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={`Enter your response for ${varName}...`}
          autoFocus
          style={{
            flex: 1,
            padding: '8px',
            border: '1px solid #ddd',
            borderRadius: '4px',
            fontSize: '14px'
          }}
        />
        <button
          onClick={handleSubmit}
          disabled={!inputValue.trim()}
          style={{
            padding: '8px 16px',
            backgroundColor: inputValue.trim() ? '#4CAF50' : '#ccc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: inputValue.trim() ? 'pointer' : 'not-allowed'
          }}
        >
          Submit
        </button>
      </div>
    </div>
  );
}