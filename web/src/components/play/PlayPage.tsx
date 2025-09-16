import { JSX, useCallback, useEffect, useRef, useState } from 'react';
import ElicitRequestHandler from './ElicitRequestHandler';
import GamePanel from './GamePanel';
import GameError from './GameError';
import TokenVisualization from './TokenVisualization';

interface XentInputMessage {
  type: 'xent_input';
  input: string;
}

interface XentConfigureMessage {
  type: 'xent_configure';
  code: string;
}

interface XentControlMessage {
  type: 'xent_control';
  command: string;
  code?: string;
}

interface XentErrorMessage {
  type: 'xent_error';
  error: string;
}

interface XentEventMessage {
  type: 'xent_event';
  event: any;
}

type XentMessage = XentInputMessage | XentConfigureMessage | XentControlMessage | XentErrorMessage | XentEventMessage;

const DEFAULT_GAME_CODE = `assign(s="Once upon a time, there was a brave knight who fought dragons and saved kingdoms.")
reveal(s)
elicit(t, 10)
reveal(t)
assign(t1=remove_common_words(t, s))
reveal(t1)
reward(xed(s | t1))`;

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
  const [currentRound, setCurrentRound] = useState<number>(0);
  const [roundScores, setRoundScores] = useState<Array<{round: number, score: number}>>([]);
  const outputIdCounter = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const appendOutput = (element: JSX.Element) => {
    setOutputs((prev) => [...prev, element]);
  };

  const sendMessage = (message: XentMessage) => {
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
      console.log('Sent message:', message);
    } else {
      console.error('WebSocket is not open. Cannot send message.');
    }
  };

  const sendInputMessage = (input: string) => {
    sendMessage({ type: 'xent_input', input });
  };

  const sendStartMessage = () => {
    sendMessage({ type: 'xent_control', command: 'start', code: code });
    setIsGameRunning(true);
    setGameCompleted(false);
    setTotalScore(null);
    setCurrentRound(0);
    setRoundScores([]);
    setOutputs([]);
    setRegisters({});
    setCurrentLine(-1);
  };

  const resetGame = () => {
    setIsGameRunning(false);
    setGameCompleted(false);
    setTotalScore(null);
    setCurrentRound(0);
    setRoundScores([]);
    setOutputs([]);
    setRegisters({});
    setCurrentLine(-1);
  };

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const message: XentMessage = JSON.parse(event.data);
      console.log('Received message:', message);

      if (message.type === 'xent_error') {
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

      if (message.type !== 'xent_event') {
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
        case 'round_started':
          setCurrentRound(data.round_index + 1); // Convert from 0-indexed to 1-indexed for display
          appendOutput(
            <div key={`output-${++outputIdCounter.current}`} style={{
              marginBottom: '10px',
              padding: '8px 12px',
              backgroundColor: '#e3f2fd',
              borderRadius: '4px',
              borderLeft: '4px solid #2196F3',
              fontSize: '14px',
              color: '#1976D2'
            }}>
              <strong>Round {data.round_index + 1} started</strong>
            </div>
          );
          break;

        case 'round_finished':
          appendOutput(
            <div key={`output-${++outputIdCounter.current}`} style={{
              marginBottom: '15px',
              padding: '8px 12px',
              backgroundColor: '#f3e5f5',
              borderRadius: '4px',
              borderLeft: '4px solid #9C27B0',
              fontSize: '14px',
              color: '#7B1FA2'
            }}>
              <strong>Round {data.round_index + 1} completed</strong>
            </div>
          );
          break;

        case 'elicit_request':
          // Always update registers from elicit_request - this is the source of truth
          if (data.registers) {
            console.log('Updating registers from elicit_request:', data.registers);
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
          // Note: Registers are updated via elicit_request events which provide the complete state
          break;

        case 'reward':
          // Extract score
          let score = 0;
          if (typeof data.value === 'number') {
            score = data.value;
          } else if (data.value && typeof data.value === 'object') {
            score = data.value.pairs.reduce((sum: number, [_, s]: [string, number]) => sum + s, 0);
          }

          // Track round score
          setRoundScores(prev => [...prev, { round: currentRound, score }]);
          setTotalScore(score);

          // Show token visualization
          appendOutput(
            <TokenVisualization
              key={`output-${++outputIdCounter.current}`}
              perTokenXent={data.value}
            />
          );

          // Add subtle round score summary
          appendOutput(
            <div key={`output-${++outputIdCounter.current}`} style={{
              marginBottom: '15px',
              padding: '10px 12px',
              backgroundColor: '#e8f5e9',
              borderRadius: '4px',
              borderLeft: '4px solid #4CAF50',
              fontSize: '14px',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center'
            }}>
              <span>
                <strong>Round {currentRound} Score:</strong> {score.toFixed(2)}
              </span>
              {roundScores.length > 0 && (
                <span style={{ fontSize: '12px', color: '#666' }}>
                  Total rounds: {roundScores.length + 1}
                </span>
              )}
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
        socket.send(JSON.stringify({ type: 'xent_configure', code: code }));
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
        <h1>XENT Interactive Play</h1>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          {connectionStatus === 'disconnected' && (
            <>
              <span style={{
                padding: '5px 10px',
                borderRadius: '5px',
                backgroundColor: '#f44336',
                color: 'white',
                fontSize: '12px'
              }}>
                ● Disconnected
              </span>
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
            </>
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
          currentRound={currentRound}
          totalRounds={roundScores.length}
        />
      </div>

      {/* Game Output Section */}
      <div style={{ backgroundColor: '#f8f9fa', padding: '15px', borderRadius: '5px' }}>
        <div style={{ marginBottom: '10px' }}>
          <h3 style={{ margin: 0 }}>Game Output</h3>
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
