import { BenchmarkStatus, BenchmarkListItem } from '../types/benchmark';

const API_BASE = '/api';

export class ApiClient {
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
}

export const apiClient = new ApiClient();