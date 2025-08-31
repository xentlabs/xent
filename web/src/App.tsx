import React, { useState, useEffect } from 'react';
import { BenchmarkList } from '@/components/BenchmarkList';
import { BenchmarkMonitor } from '@/components/BenchmarkMonitor';
import { apiClient } from '@/api/client';
import { BenchmarkListItem, BenchmarkStatus } from '@/types/benchmark';

function App() {
  const [benchmarks, setBenchmarks] = useState<BenchmarkListItem[]>([]);
  const [selectedBenchmarkId, setSelectedBenchmarkId] = useState<string | null>(null);
  const [selectedBenchmarkStatus, setSelectedBenchmarkStatus] = useState<BenchmarkStatus | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [configPath, setConfigPath] = useState('./xega_config.json');
  const [parallelGames, setParallelGames] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [isHealthy, setIsHealthy] = useState(true);

  // Check server health
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const healthy = await apiClient.checkHealth();
        setIsHealthy(healthy);
      } catch {
        setIsHealthy(false);
      }
    };
    
    checkHealth();
    const interval = setInterval(checkHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  // Load benchmarks
  const loadBenchmarks = async () => {
    try {
      const data = await apiClient.listBenchmarks();
      setBenchmarks(data.benchmarks);
    } catch (err) {
      console.error('Failed to load benchmarks:', err);
      setError('Failed to load benchmarks');
    }
  };

  useEffect(() => {
    loadBenchmarks();
    const interval = setInterval(loadBenchmarks, 5000);
    return () => clearInterval(interval);
  }, []);

  // Load selected benchmark details
  useEffect(() => {
    if (selectedBenchmarkId) {
      apiClient.getBenchmarkStatus(selectedBenchmarkId)
        .then(setSelectedBenchmarkStatus)
        .catch(err => {
          console.error('Failed to load benchmark status:', err);
          setError('Failed to load benchmark status');
        });
    } else {
      setSelectedBenchmarkStatus(null);
    }
  }, [selectedBenchmarkId]);

  const handleStartBenchmark = async () => {
    setIsStarting(true);
    setError(null);
    
    try {
      const result = await apiClient.startBenchmark(configPath, parallelGames);
      setSelectedBenchmarkId(result.benchmark_id);
      await loadBenchmarks();
    } catch (err) {
      console.error('Failed to start benchmark:', err);
      setError(err instanceof Error ? err.message : 'Failed to start benchmark');
    } finally {
      setIsStarting(false);
    }
  };

  const handleStopBenchmark = async (id: string) => {
    try {
      await apiClient.stopBenchmark(id);
      await loadBenchmarks();
    } catch (err) {
      console.error('Failed to stop benchmark:', err);
      setError('Failed to stop benchmark');
    }
  };

  if (!isHealthy) {
    return (
      <div className="min-h-screen bg-gray-100 flex items-center justify-center">
        <div className="bg-white rounded-lg shadow-lg p-8 max-w-md">
          <h2 className="text-2xl font-bold text-red-600 mb-4">Server Offline</h2>
          <p className="text-gray-600 mb-4">
            Unable to connect to the XEGA backend server.
          </p>
          <p className="text-sm text-gray-500">
            Please ensure the server is running with: <code className="bg-gray-100 px-2 py-1 rounded">xega serve</code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-bold text-gray-900">XEGA Benchmark Monitor</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-4 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
            {error}
            <button
              onClick={() => setError(null)}
              className="float-right text-red-600 hover:text-red-800"
            >
              ×
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="text-xl font-semibold mb-4">Start New Benchmark</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Config Path
                  </label>
                  <input
                    type="text"
                    value={configPath}
                    onChange={(e) => setConfigPath(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="./xega_config.json"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    Parallel Games
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="10"
                    value={parallelGames}
                    onChange={(e) => setParallelGames(parseInt(e.target.value) || 1)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  />
                </div>
                <button
                  onClick={handleStartBenchmark}
                  disabled={isStarting}
                  className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isStarting ? 'Starting...' : 'Start Benchmark'}
                </button>
              </div>
            </div>

            <BenchmarkList
              benchmarks={benchmarks}
              selectedId={selectedBenchmarkId}
              onSelect={setSelectedBenchmarkId}
              onStop={handleStopBenchmark}
            />
          </div>

          <div className="lg:col-span-2">
            {selectedBenchmarkId && selectedBenchmarkStatus ? (
              <BenchmarkMonitor
                benchmarkId={selectedBenchmarkId}
                initialStatus={selectedBenchmarkStatus}
              />
            ) : (
              <div className="bg-white rounded-lg shadow p-6">
                <p className="text-gray-500 text-center">
                  Select a benchmark from the list or start a new one
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;