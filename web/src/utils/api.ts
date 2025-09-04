import { BenchmarkStats } from '../types/benchmark';
import { PlayerConfig } from '../components/PlayerConfigForm';

export async function fetchBenchmarkStats(benchmarkId: string): Promise<BenchmarkStats> {
  const response = await fetch(`/api/benchmarks/${benchmarkId}/stats`);
  if (!response.ok) {
    throw new Error(`Failed to fetch benchmark stats: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchBenchmarkList(): Promise<string[]> {
  const response = await fetch('/api/benchmarks');
  if (!response.ok) {
    throw new Error(`Failed to fetch benchmarks: ${response.statusText}`);
  }
  return response.json();
}

export async function runBenchmark(benchmarkId: string): Promise<any> {
  const response = await fetch(`/api/benchmarks/${benchmarkId}/run`, {
    method: 'POST',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to start benchmark');
  }
  return response.json();
}

export async function deleteBenchmarkResults(benchmarkId: string): Promise<any> {
  const response = await fetch(`/api/benchmarks/${benchmarkId}/results`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete results');
  }
  return response.json();
}

export async function addPlayersToBenchmark(
  benchmarkId: string,
  players: PlayerConfig[]
): Promise<any> {
  const response = await fetch(`/api/benchmarks/${benchmarkId}/add-players`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ players }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to add players');
  }

  return response.json();
}
