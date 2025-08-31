import { useEffect, useRef, useState } from 'react';
import { WebSocketMessage } from '../types/benchmark';

interface UseWebSocketOptions {
  onMessage?: (message: WebSocketMessage) => void;
}

export function useWebSocket(
  benchmarkId: string | null,
  options: UseWebSocketOptions = {}
) {
  const [isConnected, setIsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const { onMessage } = options;

  useEffect(() => {
    if (!benchmarkId) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/benchmarks/${benchmarkId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
    };

    ws.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data);
        onMessage?.(message);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      ws.close();
    };
  }, [benchmarkId, onMessage]);

  return { isConnected };
}