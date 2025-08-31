import React, { useState, useEffect } from 'react';
import { BenchmarkList } from './components/BenchmarkList';
import { BenchmarkMonitor } from './components/BenchmarkMonitor';
import { apiClient } from './api/client';
import { BenchmarkListItem, BenchmarkStatus } from './types/benchmark';

function App() {
  const [benchmarks, setBenchmarks] = useState<BenchmarkListItem[]>([]);
  const [selectedBenchmarkId, setSelectedBenchmarkId] = useState<string | null>(null);
  const [selectedBenchmarkStatus, setSelectedBenchmarkStatus] = useState<BenchmarkStatus | null>(null);

  // Load benchmarks
  const loadBenchmarks = async () => {
    try {
      const data = await apiClient.listBenchmarks();
      setBenchmarks(data.benchmarks);
    } catch (err) {
      console.error('Failed to load benchmarks:', err);
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
        });
    } else {
      setSelectedBenchmarkStatus(null);
    }
  }, [selectedBenchmarkId]);

  return (
    <div className="min-h-screen bg-gray-100">
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <h1 className="text-3xl font-bold text-gray-900">XEGA Benchmark Monitor</h1>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-1">
            <BenchmarkList
              benchmarks={benchmarks}
              selectedId={selectedBenchmarkId}
              onSelect={setSelectedBenchmarkId}
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
                  Select a benchmark from the list to view details
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