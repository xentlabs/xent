import { ChartData, LineChartData, GameDetails } from '../types/benchmark';

/**
 * Transform score record to chart data format
 */
export function transformToChartData(scores: Record<string, number>): ChartData[] {
  return Object.entries(scores)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value);
}

/**
 * Transform per-iteration player data to line chart format
 */
export function transformToLineChartData(
  playerData: Record<string, number[]>
): LineChartData[] {
  if (!playerData || Object.keys(playerData).length === 0) {
    return [];
  }

  // Find the maximum length across all players
  const maxLength = Math.max(...Object.values(playerData).map(arr => arr.length));
  
  const lineData: LineChartData[] = [];
  
  for (let i = 0; i < maxLength; i++) {
    const dataPoint: LineChartData = { iteration: i + 1 }; // 1-indexed
    
    Object.entries(playerData).forEach(([playerId, values]) => {
      dataPoint[playerId] = values[i]; // Can be undefined if player has fewer iterations
    });
    
    lineData.push(dataPoint);
  }
  
  return lineData;
}

/**
 * Calculate average scores across all iterations for each player
 */
export function calculateAverageScores(
  iterationData: Record<string, number[]>
): Record<string, number> {
  const averages: Record<string, number> = {};
  
  Object.entries(iterationData).forEach(([playerId, scores]) => {
    if (scores.length > 0) {
      const sum = scores.reduce((acc, score) => acc + score, 0);
      averages[playerId] = sum / scores.length;
    } else {
      averages[playerId] = 0;
    }
  });
  
  return averages;
}

/**
 * Get the latest (most recent) scores for each player
 */
export function getLatestScores(
  iterationData: Record<string, number[]>
): Record<string, number> {
  const latestScores: Record<string, number> = {};
  
  Object.entries(iterationData).forEach(([playerId, scores]) => {
    latestScores[playerId] = scores.length > 0 ? scores[scores.length - 1] : 0;
  });
  
  return latestScores;
}

/**
 * Get summary statistics for a game
 */
export function getGameSummary(gameDetails: GameDetails) {
  const players = Object.keys(gameDetails.iterations_by_player);
  const totalIterations = Math.max(
    ...Object.values(gameDetails.iterations_by_player).map(arr => arr.length)
  );
  
  return {
    playerCount: players.length,
    totalIterations,
    players,
  };
}