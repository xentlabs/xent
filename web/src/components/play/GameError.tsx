interface GameErrorProps {
  error: string;
  isWarning?: boolean;
}

export default function GameError({ error, isWarning = false }: GameErrorProps) {
  return (
    <div style={{ 
      marginBottom: '15px', 
      padding: '12px', 
      backgroundColor: isWarning ? '#fff3cd' : '#f8d7da', 
      borderRadius: '5px',
      border: `1px solid ${isWarning ? '#ffc107' : '#f5c6cb'}`
    }}>
      <strong style={{ color: isWarning ? '#856404' : '#721c24' }}>
        {isWarning ? '⚠️ Warning' : '❌ Error'}:
      </strong>
      <span style={{ marginLeft: '8px', color: isWarning ? '#856404' : '#721c24' }}>
        {error}
      </span>
    </div>
  );
}