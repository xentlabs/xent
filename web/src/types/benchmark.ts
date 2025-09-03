export interface BenchmarkStats {
  status: 'ready' | 'running' | 'completed';
  overall_scores: Record<string, number>;
  per_game_scores: Record<string, Record<string, number>>;
  per_game_details: Record<string, GameDetails>;
  metadata: {
    benchmark_id: string;
    num_players: number;
    num_games: number;
    num_maps: number;
    expected_results: number;
    actual_results: number;
  };
  config: any; // Full benchmark configuration
}

export interface GameDetails {
  code: string;
  iterations_by_player: Record<string, number[]>;
  arms_by_player: Record<string, number[]>;
  round_scores_by_player: Record<string, number[]>;
}

export interface ChartData {
  name: string;
  value: number;
}

export interface LineChartData {
  iteration: number;
  [playerId: string]: number | undefined;
}