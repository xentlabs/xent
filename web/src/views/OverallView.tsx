import { ScoreBarChart, LeaderboardTable } from '../components';
import { transformToChartData } from '../utils/chartData';
import { BenchmarkStats } from '../types/benchmark';

interface OverallViewProps {
  stats: BenchmarkStats;
  className?: string;
}

export default function OverallView({ stats, className = '' }: OverallViewProps) {
  const { overall_scores, metadata } = stats;
  
  // Transform data for charts
  const chartData = transformToChartData(overall_scores);
  
  const hasData = Object.keys(overall_scores).length > 0;

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Summary Statistics */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Summary Statistics</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{metadata.num_players}</div>
            <div className="text-sm text-gray-600">Players</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{metadata.num_games}</div>
            <div className="text-sm text-gray-600">Games</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">{metadata.num_maps}</div>
            <div className="text-sm text-gray-600">Maps</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-orange-600">
              {Object.keys(overall_scores).length}
            </div>
            <div className="text-sm text-gray-600">Active Players</div>
          </div>
        </div>
      </div>

      {hasData ? (
        <>
          {/* Charts Section */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Leaderboard Table */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <LeaderboardTable 
                data={chartData}
                title="Rankings"
              />
            </div>
            
            {/* Bar Chart */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <ScoreBarChart 
                data={chartData}
                title="Score Distribution"
                height={300}
              />
            </div>
          </div>

          {/* Per-Game Summary */}
          {Object.keys(stats.per_game_scores).length > 0 && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Per-Game Breakdown</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {Object.entries(stats.per_game_scores).map(([gameName, gameScores]) => {
                  const gameChartData = transformToChartData(gameScores);
                  const topPlayer = gameChartData[0];
                  const playerCount = Object.keys(gameScores).length;
                  
                  return (
                    <div key={gameName} className="border border-gray-200 rounded-lg p-4">
                      <h4 className="font-medium text-gray-900 mb-2">{gameName}</h4>
                      <div className="space-y-2">
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Top Player:</span>
                          <span className="font-medium">{topPlayer?.name || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Top Score:</span>
                          <span className="font-mono">{topPlayer?.value.toFixed(2) || 'N/A'}</span>
                        </div>
                        <div className="flex justify-between text-sm">
                          <span className="text-gray-600">Players:</span>
                          <span>{playerCount}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </>
      ) : (
        /* No Data State */
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12">
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 text-gray-400">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={1.5} 
                  d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" 
                />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Results Yet</h3>
            <p className="text-gray-500 max-w-sm mx-auto">
              {stats.status === 'ready'
                ? 'This benchmark is ready to run. Click "Start Benchmark" to begin execution.'
                : stats.status === 'running' 
                ? 'The benchmark is currently running. Results will appear as they become available.'
                : 'No benchmark results found. Make sure the benchmark has been executed.'
              }
            </p>
          </div>
        </div>
      )}
    </div>
  );
}