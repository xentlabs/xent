interface GamePanelProps {
  code: string[];
  currentLine: number;
  registers: Record<string, string | string[]>;
  currentRound?: number;
  totalRounds?: number;
}

export default function GamePanel({ code, currentLine, registers, currentRound = 0, totalRounds = 0 }: GamePanelProps) {
  return (
    <div style={{ backgroundColor: '#f8f9fa', padding: '15px', borderRadius: '5px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
        <h3 style={{ margin: 0 }}>Game State</h3>
        {currentRound > 0 && (
          <div style={{
            fontSize: '14px',
            color: '#666',
            backgroundColor: '#e3f2fd',
            padding: '4px 8px',
            borderRadius: '4px',
            border: '1px solid #bbdefb'
          }}>
            Round: {currentRound} | Completed: {totalRounds}
          </div>
        )}
      </div>

      {/* Code Execution Display */}
      <div style={{ marginBottom: '15px' }}>
        <h4 style={{ fontSize: '14px', marginBottom: '10px' }}>Code Execution</h4>
        <div style={{
          backgroundColor: 'white',
          border: '1px solid #ddd',
          borderRadius: '3px',
          padding: '10px',
          maxHeight: '150px',
          overflowY: 'auto',
          fontFamily: 'monospace',
          fontSize: '12px'
        }}>
          {code.length === 0 ? (
            <div style={{ color: '#666' }}>No code loaded</div>
          ) : (
            code.map((line, index) => (
              <div
                key={index}
                style={{
                  padding: '2px 5px',
                  backgroundColor: currentLine === index ? '#fffbdd' : 'transparent',
                  borderLeft: currentLine === index ? '3px solid #ffc107' : '3px solid transparent',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}
              >
                <span style={{ color: '#666', marginRight: '10px', minWidth: '20px', display: 'inline-block' }}>
                  {index + 1}
                </span>
                {line}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Registers Display */}
      <div>
        <h4 style={{ fontSize: '14px', marginBottom: '10px' }}>Registers</h4>
        <div style={{
          backgroundColor: 'white',
          border: '1px solid #ddd',
          borderRadius: '3px',
          padding: '10px',
          minHeight: '40px'
        }}>
          {(() => {
            const nonEmptyRegisters = Object.entries(registers).filter(([_, value]) =>
              value && ((typeof value === 'string' && value.trim() !== '') || (Array.isArray(value) && value.length > 0))
            );

            if (nonEmptyRegisters.length === 0) {
              return (
                <div style={{ color: '#666', fontStyle: 'italic' }}>No registers set</div>
              );
            }

            return (
              <table style={{ width: '100%', fontSize: '12px' }}>
                <tbody>
                  {nonEmptyRegisters.map(([key, value]) => (
                    <tr key={key}>
                      <td style={{
                        fontWeight: 'bold',
                        paddingRight: '15px',
                        color: '#2196F3',
                        verticalAlign: 'top',
                        width: '60px'
                      }}>
                        {key}:
                      </td>
                      <td style={{
                        fontFamily: 'monospace',
                        wordBreak: 'break-word',
                        whiteSpace: 'pre-wrap'
                      }}>
                        {value}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            );
          })()}
        </div>
      </div>
    </div>
  );
}
