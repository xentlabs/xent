import { JSX, useCallback, useEffect, useRef, useState } from 'react';
import ElicitRequestHandler from './ElicitRequestHandler';
import GamePanel from './GamePanel';
import GameError from './GameError';
import TokenVisualization from './TokenVisualization';

interface XegaInputMessage {
  type: 'xega_input';
  input: string;
}

interface XegaConfigureMessage {
  type: 'xega_configure';
  code: string;
}

interface XegaControlMessage {
  type: 'xega_control';
  command: string;
}

interface XegaErrorMessage {
  type: 'xega_error';
  error: string;
}

interface XegaEventMessage {
  type: 'xega_event';
  event: any;
}

type XegaMessage = XegaInputMessage | XegaConfigureMessage | XegaControlMessage | XegaErrorMessage | XegaEventMessage;

const PRESET_GAMES = {
  simple: {
    name: "Simple Story Completion",
    code: `assign(s="Once upon a time, there was a brave knight who fought dragons and saved kingdoms.")
reveal(black, s)
elicit(black, t, 10)
reveal(black, t)
assign(t1=remove_common_words(t, s))
reveal(black, t1)
reward(black, xed(s | t1))`
  },
  interactive: {
    name: "Interactive Story",
    code: `assign(s=story())
reveal(black, s)
elicit(black, x, 10)
assign(x1=remove_common_words(x, s))
reward(black, xed(s | x1))`
  },
  multi_turn: {
    name: "Multi-turn Conversation",
    code: `assign(prompt="What is your favorite color?")
reveal(black, prompt)
elicit(black, color, 5)
assign(response="Interesting! " + color + " is a nice choice.")
reveal(black, response)
reward(black, 0)`
  }
};

const DEFAULT_GAME_CODE = PRESET_GAMES.simple.code;

export default function PlayPage({ onBack }: { onBack: () => void }) {
  const ws = useRef<WebSocket | null>(null);
  const [code, setCode] = useState<string>(DEFAULT_GAME_CODE);
  const [codeLines, setCodeLines] = useState<string[]>([]);
  const [currentLine, setCurrentLine] = useState<number>(-1);
  const [registers, setRegisters] = useState<Record<string, string>>({});
  const [outputs, setOutputs] = useState<JSX.Element[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected'>('disconnected');
  const [isGameRunning, setIsGameRunning] = useState(false);
  const [gameCompleted, setGameCompleted] = useState(false);
  const [totalScore, setTotalScore] = useState<number | null>(null);
  const outputIdCounter = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const appendOutput = (element: JSX.Element) => {
    setOutputs((prev) => [...prev, element]);
  };

  const sendMessage = (message: XegaMessage) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
      console.log('Sent message:', message);
    } else {
      console.error('WebSocket is not open. Cannot send message.');
    }
  };

  const sendInputMessage = (input: string) => {
    sendMessage({ type: 'xega_input', input });
  };

  const sendConfigureMessage = (newCode: string) => {
    sendMessage({ type: 'xega_configure', code: newCode });
    setCode(newCode);
    setCodeLines(newCode.split('\n'));
  };

  const sendStartMessage = () => {
    sendMessage({ type: 'xega_control', command: 'start' });
    setIsGameRunning(true);
    setGameCompleted(false);
    setTotalScore(null);
    setOutputs([]);
    setRegisters({});
    setCurrentLine(-1);
  };

  const resetGame = () => {
    setIsGameRunning(false);
    setGameCompleted(false);
    setTotalScore(null);
    setOutputs([]);
    setRegisters({});
    setCurrentLine(-1);
  };

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: XegaMessage = JSON.parse(event.data);
      console.log('Received message:', message);

      if (message.type === 'xega_error') {
        console.error('Error from server:', message.error);
        appendOutput(
          <GameError
            key={`output-${++outputIdCounter.current}`}
            error={message.error}
          />
        );
        setIsGameRunning(false);
        return;
      }

      if (message.type !== 'xega_event') {
        console.warn('Received non-event message:', message);
        return;
      }

      const data = message.event;
      console.log('Received event:', data);

      // Update current line if provided
      if (data.line_num !== undefined) {
        setCurrentLine(data.line_num);
      }

      switch (data.type) {
        case 'elicit_request':
          // Update registers if provided
          if (data.registers) {
            setRegisters(data.registers);
          }
          
          appendOutput(
            <ElicitRequestHandler
              key={`output-${++outputIdCounter.current}`}
              varName={data.var_name}
              maxLen={data.max_len}
              onSubmit={(text: string) => {
                sendInputMessage(text);
              }}
            />
          );
          break;

        case 'elicit_response':
          appendOutput(
            <div key={`output-${++outputIdCounter.current}`} style={{ marginBottom: '10px' }}>
              <strong>Response:</strong> {data.response}
            </div>
          );
          break;

        case 'reveal':
          appendOutput(
            <div key={`output-${++outputIdCounter.current}`} style={{ marginBottom: '10px' }}>
              <strong>Revealed:</strong> {JSON.stringify(data.values)}
            </div>
          );
          // Update registers based on revealed values
          if (data.values && Array.isArray(data.values) && data.line) {
            // Parse the reveal statement to extract variable names
            // Format: reveal(player, var1, var2, ...)
            const revealMatch = data.line.match(/reveal\s*\(\s*\w+\s*((?:,\s*\w+\s*)*)\)/);
            if (revealMatch) {
              const varsString = revealMatch[1];
              if (varsString) {
                const varNames = varsString.split(',').map((v: string) => v.trim()).filter((v: string) => v);
                varNames.forEach((varName: string, index: number) => {
                  if (data.values[index] !== undefined) {
                    setRegisters(prev => ({
                      ...prev,
                      [varName]: String(data.values[index])
                    }));
                  }
                });
              }
            }
          }
          break;

        case 'reward':
          // Extract total score
          let score = 0;
          if (typeof data.value === 'number') {
            score = data.value;
          } else if (data.value && typeof data.value === 'object') {
            if (data.value.total_xent) {
              score = typeof data.value.total_xent === 'function' 
                ? data.value.total_xent() 
                : data.value.total_xent;
            } else if (Array.isArray(data.value)) {
              score = data.value.reduce((sum: number, [_, s]: [string, number]) => sum + s, 0);
            }
          }
          
          setTotalScore(score);
          setGameCompleted(true);
          setIsGameRunning(false);
          
          appendOutput(
            <TokenVisualization
              key={`output-${++outputIdCounter.current}`}
              perTokenXent={data.value}
            />
          );
          
          // Add completion message
          appendOutput(
            <div key={`output-${++outputIdCounter.current}`} style={{ 
              marginTop: '20px', 
              padding: '15px', 
              backgroundColor: '#e8f5e9', 
              borderRadius: '5px',
              border: '2px solid #4CAF50',
              textAlign: 'center'
            }}>
              <h3 style={{ color: '#2e7d32', margin: '0 0 10px 0' }}>🎉 Game Complete!</h3>
              <p style={{ margin: '5px 0', fontSize: '18px', fontWeight: 'bold' }}>
                Final Score: {score.toFixed(2)}
              </p>
              <button
                onClick={resetGame}
                style={{
                  marginTop: '10px',
                  padding: '8px 16px',
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  border: 'none',
                  borderRadius: '4px',
                  cursor: 'pointer'
                }}
              >
                Play Again
              </button>
            </div>
          );
          break;

        case 'failed_ensure':
          appendOutput(
            <GameError
              key={`output-${++outputIdCounter.current}`}
              error={`Failed ensure. Moving execution to ${data.beacon} - Ensure Results: ${data.ensure_results?.join(', ')}`}
              isWarning
            />
          );
          break;

        default:
          console.warn('Unknown event type:', data.type);
          appendOutput(
            <div key={`output-${++outputIdCounter.current}`} style={{ marginBottom: '10px' }}>
              Unknown event: {JSON.stringify(data)}
            </div>
          );
      }
    } catch (error) {
      console.error('Failed to parse message:', error);
    }
  }, []);

  // WebSocket connection management with retry logic
  const connectWebSocket = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      return; // Already connected
    }

    setConnectionStatus('connecting');
    
    // Connect to WebSocket
    const socket = new WebSocket('ws://localhost:8000/ws');
    ws.current = socket;

    socket.onopen = () => {
      console.log('WebSocket connection established');
      setConnectionStatus('connected');
      // Clear any reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      // Configure with current code
      if (socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify({ type: 'xega_configure', code: code }));
      }
    };

    socket.onmessage = (event) => {
      handleMessage(event);
    };

    socket.onclose = (event) => {
      setConnectionStatus('disconnected');
      setIsGameRunning(false);
      if (event.wasClean) {
        console.log(`Connection closed cleanly, code=${event.code} reason=${event.reason}`);
      } else {
        console.error('Connection died unexpectedly');
        // Attempt to reconnect after 3 seconds
        if (!reconnectTimeoutRef.current) {
          reconnectTimeoutRef.current = setTimeout(() => {
            console.log('Attempting to reconnect...');
            connectWebSocket();
          }, 3000);
        }
      }
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionStatus('disconnected');
    };
  }, [code, handleMessage]);

  // Initial connection
  useEffect(() => {
    connectWebSocket();

    return () => {
      // Cleanup on component unmount (SPA navigation)
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (ws.current) {
        ws.current.close(1000, "User navigated away");
      }
    };
  }, [connectWebSocket]);

  // Handle browser refresh/close
  useEffect(() => {
    const handleBeforeUnload = () => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.close(1000, "Page unloading");
      }
    };
    
    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, []);

  useEffect(() => {
    setCodeLines(code.split('\n'));
  }, [code]);

  return (
    <div style={{ padding: '20px', fontFamily: 'system-ui, sans-serif', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>XEGA Interactive Play</h1>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <span style={{ 
            padding: '5px 10px', 
            borderRadius: '5px',
            backgroundColor: connectionStatus === 'connected' ? '#4CAF50' : connectionStatus === 'connecting' ? '#FFA500' : '#f44336',
            color: 'white',
            fontSize: '12px'
          }}>
            {connectionStatus === 'connected' ? '● Connected' : connectionStatus === 'connecting' ? '● Connecting...' : '● Disconnected'}
          </span>
          {connectionStatus === 'disconnected' && (
            <button
              onClick={connectWebSocket}
              style={{ 
                padding: '6px 12px', 
                backgroundColor: '#2196F3', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px', 
                cursor: 'pointer',
                fontSize: '12px'
              }}
            >
              Reconnect
            </button>
          )}
          <button
            onClick={onBack}
            style={{ padding: '8px 16px', backgroundColor: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
          >
            Back to Dashboard
          </button>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
        {/* Game Code Section */}
        <div style={{ backgroundColor: '#f8f9fa', padding: '15px', borderRadius: '5px' }}>
          <h3>Game Code</h3>
          
          {/* Preset Games Selector */}
          <div style={{ marginBottom: '10px' }}>
            <label style={{ fontSize: '12px', color: '#666', marginRight: '10px' }}>Load preset:</label>
            <select
              onChange={(e) => {
                if (e.target.value && PRESET_GAMES[e.target.value as keyof typeof PRESET_GAMES]) {
                  setCode(PRESET_GAMES[e.target.value as keyof typeof PRESET_GAMES].code);
                }
              }}
              disabled={isGameRunning}
              style={{
                padding: '4px 8px',
                fontSize: '12px',
                border: '1px solid #ddd',
                borderRadius: '3px',
                cursor: isGameRunning ? 'not-allowed' : 'pointer'
              }}
            >
              <option value="">-- Select Preset --</option>
              {Object.entries(PRESET_GAMES).map(([key, game]) => (
                <option key={key} value={key}>{game.name}</option>
              ))}
            </select>
          </div>
          
          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            style={{ 
              width: '100%', 
              minHeight: '200px', 
              fontFamily: 'monospace', 
              fontSize: '12px',
              padding: '10px',
              border: '1px solid #ddd',
              borderRadius: '3px'
            }}
            disabled={isGameRunning}
          />
          <div style={{ marginTop: '10px', display: 'flex', gap: '10px' }}>
            <button
              onClick={() => sendConfigureMessage(code)}
              disabled={connectionStatus !== 'connected' || isGameRunning}
              style={{ 
                padding: '8px 16px', 
                backgroundColor: '#2196F3', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px', 
                cursor: connectionStatus === 'connected' && !isGameRunning ? 'pointer' : 'not-allowed',
                opacity: connectionStatus === 'connected' && !isGameRunning ? 1 : 0.6
              }}
            >
              Update Code
            </button>
            <button
              onClick={sendStartMessage}
              disabled={connectionStatus !== 'connected' || isGameRunning}
              style={{ 
                padding: '8px 16px', 
                backgroundColor: '#4CAF50', 
                color: 'white', 
                border: 'none', 
                borderRadius: '4px', 
                cursor: connectionStatus === 'connected' && !isGameRunning ? 'pointer' : 'not-allowed',
                opacity: connectionStatus === 'connected' && !isGameRunning ? 1 : 0.6
              }}
            >
              {isGameRunning ? 'Game Running...' : 'Start Game'}
            </button>
          </div>
        </div>

        {/* Game State Section */}
        <GamePanel
          code={codeLines}
          currentLine={currentLine}
          registers={registers}
        />
      </div>

      {/* Game Output Section */}
      <div style={{ backgroundColor: '#f8f9fa', padding: '15px', borderRadius: '5px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
          <h3 style={{ margin: 0 }}>Game Output</h3>
          {outputs.length > 0 && !isGameRunning && (
            <button
              onClick={() => setOutputs([])}
              style={{
                padding: '4px 8px',
                backgroundColor: '#ff9800',
                color: 'white',
                border: 'none',
                borderRadius: '3px',
                cursor: 'pointer',
                fontSize: '12px'
              }}
            >
              Clear Output
            </button>
          )}
        </div>
        <div style={{ 
          backgroundColor: 'white', 
          border: '1px solid #ddd', 
          borderRadius: '3px', 
          padding: '15px',
          minHeight: '200px',
          maxHeight: '400px',
          overflowY: 'auto'
        }}>
          {outputs.length === 0 ? (
            <div style={{ color: '#666', fontStyle: 'italic' }}>
              {isGameRunning ? 'Game is running...' : 'Click "Start Game" to begin'}
            </div>
          ) : (
            outputs
          )}
        </div>
      </div>
    </div>
  );
}