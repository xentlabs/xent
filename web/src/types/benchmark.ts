export interface BenchmarkConfig {
  metadata: {
    benchmark_id: string;
    xega_version: string;
    judge_model: string;
    num_rounds_per_game: number;
    seed: string;
  };
  games: Array<{
    name: string;
    code: string;
  }>;
  players: Array<{
    id: string;
    type: string;
    [key: string]: any;
  }>;
}

export interface BenchmarkResult {
  game_results: Array<{
    game_map: {
      name: string;
      map_seed: string;
      code: string;
    };
    player: {
      id: string;
      type: string;
    };
    score: number;
    token_usage: {
      input_tokens: number;
      output_tokens: number;
    };
  }>;
  metadata: {
    benchmark_id: string;
    xega_version: string;
  };
}

export interface BenchmarkStatus {
  id: string;
  exists: boolean;
  progress?: {
    completed: number;
    total: number;
    percentage: number;
  };
  config?: BenchmarkConfig;
  results?: BenchmarkResult;
}

export interface BenchmarkListItem {
  id: string;
  path: string;
  created: number | null;
  has_config: boolean;
}

export interface WebSocketMessage {
  type: 'config_update' | 'results_update' | 'heartbeat' | 'error';
  benchmark_id: string;
  progress?: {
    completed: number;
    total: number;
    percentage: number;
  };
  data?: any;
  message?: string;
}