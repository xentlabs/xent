import React from 'react';
import { BenchmarkResult } from '@/types/benchmark';

interface ResultsTableProps {
  results: BenchmarkResult;
}

export function ResultsTable({ results }: ResultsTableProps) {
  const gameResults = results.game_results || [];

  // Group results by game and calculate aggregates
  const groupedResults = gameResults.reduce((acc, result) => {
    const key = `${result.game_map.name}-${result.player.id}`;
    if (!acc[key]) {
      acc[key] = {
        game: result.game_map.name,
        player: result.player.id,
        scores: [],
        totalTokens: 0,
      };
    }
    acc[key].scores.push(result.score);
    acc[key].totalTokens += (result.token_usage?.input_tokens || 0) + (result.token_usage?.output_tokens || 0);
    return acc;
  }, {} as Record<string, any>);

  const summaryData = Object.values(groupedResults).map((group: any) => ({
    ...group,
    avgScore: group.scores.reduce((a: number, b: number) => a + b, 0) / group.scores.length,
    maxScore: Math.max(...group.scores),
    minScore: Math.min(...group.scores),
  }));

  return (
    <div>
      <h3 className="text-lg font-semibold mb-2">Results</h3>
      
      {summaryData.length === 0 ? (
        <p className="text-gray-500">No results yet...</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Game
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Player
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Avg Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Max Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Min Score
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Total Tokens
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {summaryData.map((row, index) => (
                <tr key={index}>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {row.game}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {row.player}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {row.avgScore.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {row.maxScore.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {row.minScore.toFixed(2)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    {row.totalTokens.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="mt-4 text-sm text-gray-600">
        Total game results: {gameResults.length}
      </div>
    </div>
  );
}