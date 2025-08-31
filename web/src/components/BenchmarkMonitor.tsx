import React, { useEffect, useState } from 'react';
import { BenchmarkStatus, WebSocketMessage } from '@/types/benchmark';
import { useWebSocket } from '@/hooks/useWebSocket';
import { ProgressBar } from './ProgressBar';
import { ResultsTable } from './ResultsTable';

interface BenchmarkMonitorProps {
  benchmarkId: string;
  initialStatus?: BenchmarkStatus;
}

export function BenchmarkMonitor({ benchmarkId, initialStatus }: BenchmarkMonitorProps) {
  const [status, setStatus] = useState<BenchmarkStatus | null>(initialStatus || null);
  const [progress, setProgress] = useState<{
    completed: number;
    total: number;
    percentage: number;
  } | null>(null);

  const { isConnected, lastMessage } = useWebSocket(benchmarkId, {
    onMessage: (message: WebSocketMessage) => {
      console.log('Received WebSocket message:', message);
      
      if (message.type === 'config_update' && message.data) {
        setStatus(prev => prev ? { ...prev, config: message.data } : null);
      } else if (message.type === 'results_update') {
        if (message.progress) {
          setProgress(message.progress);
        }
        if (message.data) {
          setStatus(prev => prev ? { ...prev, results: message.data } : null);
        }
      }
    },
  });

  useEffect(() => {
    if (initialStatus) {
      setStatus(initialStatus);
      if (initialStatus.progress) {
        setProgress(initialStatus.progress);
      }
    }
  }, [initialStatus]);

  if (!status) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <p className="text-gray-500">Loading benchmark data...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h2 className="text-2xl font-bold">{benchmarkId}</h2>
            <p className="text-gray-600">
              Status: {status.is_running ? 'Running' : 'Completed'}
            </p>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        {progress && (
          <div className="mb-6">
            <ProgressBar
              completed={progress.completed}
              total={progress.total}
              percentage={progress.percentage}
            />
          </div>
        )}

        {status.config && (
          <div className="mb-6">
            <h3 className="text-lg font-semibold mb-2">Configuration</h3>
            <div className="bg-gray-50 p-4 rounded">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="font-medium">Judge Model:</span>{' '}
                  {status.config.metadata.judge_model}
                </div>
                <div>
                  <span className="font-medium">Rounds per Game:</span>{' '}
                  {status.config.metadata.num_rounds_per_game}
                </div>
                <div>
                  <span className="font-medium">Games:</span>{' '}
                  {status.config.games?.length || 0}
                </div>
                <div>
                  <span className="font-medium">Players:</span>{' '}
                  {status.config.players?.length || 0}
                </div>
              </div>
            </div>
          </div>
        )}

        {status.results && (
          <ResultsTable results={status.results} />
        )}
      </div>
    </div>
  );
}