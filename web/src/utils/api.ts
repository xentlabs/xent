import { BenchmarkStats } from '../types/benchmark';
import { PlayerConfig } from '../components/PlayerConfigForm';

// API Keys types
export interface KeySummaryItem {
  name: string;
  set: boolean;
  source: 'env' | 'keystore' | 'unset';
  last4?: string;
}

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

export async function fetchAvailableGames(): Promise<any[]> {
  const response = await fetch('/api/games');
  if (!response.ok) {
    throw new Error(`Failed to fetch games: ${response.statusText}`);
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

// API Keys endpoints
export async function getApiKeys(): Promise<KeySummaryItem[]> {
  const response = await fetch('/api/keys');
  if (!response.ok) {
    throw new Error(`Failed to fetch API keys: ${response.statusText}`);
  }
  return response.json();
}

export async function saveApiKeys(keys: Record<string, string>): Promise<KeySummaryItem[]> {
  const response = await fetch('/api/keys', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ keys }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to save API keys');
  }
  return response.json();
}

export async function deleteApiKey(name: string, unsetEnv: boolean = false): Promise<KeySummaryItem[]> {
  const response = await fetch(`/api/keys/${encodeURIComponent(name)}?unset_env=${unsetEnv ? 'true' : 'false'}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to delete API key');
  }
  return response.json();
}
