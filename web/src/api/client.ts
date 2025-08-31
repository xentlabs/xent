import { BenchmarkStatus, BenchmarkListItem } from '@/types/benchmark';

const API_BASE = '/api';

export class ApiClient {
  async startBenchmark(configPath: string = './xega_config.json', parallelGames: number = 1) {
    const response = await fetch(`${API_BASE}/benchmarks/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        config_path: configPath,
        results_dir: './results',
        parallel_games: parallelGames,
        regenerate_id: false,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Failed to start benchmark: ${response.statusText}`);
    }
    
    return response.json();
  }

  async getBenchmarkStatus(benchmarkId: string): Promise<BenchmarkStatus> {
    const response = await fetch(`${API_BASE}/benchmarks/${benchmarkId}/status`);
    
    if (!response.ok) {
      throw new Error(`Failed to get benchmark status: ${response.statusText}`);
    }
    
    return response.json();
  }

  async listBenchmarks(): Promise<{ benchmarks: BenchmarkListItem[]; total: number }> {
    const response = await fetch(`${API_BASE}/benchmarks`);
    
    if (!response.ok) {
      throw new Error(`Failed to list benchmarks: ${response.statusText}`);
    }
    
    return response.json();
  }

  async stopBenchmark(benchmarkId: string) {
    const response = await fetch(`${API_BASE}/benchmarks/${benchmarkId}/stop`, {
      method: 'POST',
    });
    
    if (!response.ok) {
      throw new Error(`Failed to stop benchmark: ${response.statusText}`);
    }
    
    return response.json();
  }

  async checkHealth() {
    const response = await fetch(`${API_BASE}/health`);
    return response.ok;
  }
}

export const apiClient = new ApiClient();