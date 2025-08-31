import React from 'react';
import { BenchmarkListItem } from '../types/benchmark';

interface BenchmarkListProps {
  benchmarks: BenchmarkListItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function BenchmarkList({ benchmarks, selectedId, onSelect }: BenchmarkListProps) {
  const formatDate = (timestamp: number | null) => {
    if (!timestamp) return 'Unknown';
    return new Date(timestamp * 1000).toLocaleString();
  };

  return (
    <div className="bg-white rounded-lg shadow p-4">
      <h2 className="text-xl font-semibold mb-4">Benchmarks</h2>
      <div className="space-y-2">
        {benchmarks.length === 0 ? (
          <p className="text-gray-500">No benchmarks found</p>
        ) : (
          benchmarks.map((benchmark) => (
            <div
              key={benchmark.id}
              className={`p-3 border rounded cursor-pointer transition-colors ${
                selectedId === benchmark.id
                  ? 'border-blue-500 bg-blue-50'
                  : 'border-gray-200 hover:bg-gray-50'
              }`}
              onClick={() => onSelect(benchmark.id)}
            >
              <div className="font-medium">{benchmark.id}</div>
              <div className="text-sm text-gray-500">
                Created: {formatDate(benchmark.created)}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}