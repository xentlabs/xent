import { useState, useEffect } from 'react';
import { fetchBenchmarkStats, runBenchmark, deleteBenchmarkResults, addPlayersToBenchmark } from '../utils/api';
import { BenchmarkStats } from '../types/benchmark';
import OverallView from './OverallView';
import Modal from '../components/Modal';
import PlayerConfigForm, { PlayerConfig } from '../components/PlayerConfigForm';

interface BenchmarkDashboardProps {
  benchmarkId: string;
  onBack: () => void;
}

export default function BenchmarkDashboard({ benchmarkId, onBack }: BenchmarkDashboardProps) {
  const [stats, setStats] = useState<BenchmarkStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentView, setCurrentView] = useState<'overall' | string>('overall');
  const [configExpanded, setConfigExpanded] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [showAddPlayerModal, setShowAddPlayerModal] = useState(false);
  const [addingPlayers, setAddingPlayers] = useState(false);

  // Fetch benchmark stats
  const loadStats = async () => {
    try {
      setLoading(true);
      setError(null);
      const benchmarkStats = await fetchBenchmarkStats(benchmarkId);
      setStats(benchmarkStats);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load benchmark stats');
    } finally {
      setLoading(false);
    }
  };

  // Handle running benchmark
  const handleRunBenchmark = async () => {
    if (isRunning) return;

    try {
      setIsRunning(true);
      await runBenchmark(benchmarkId);
      // Start polling for updates
      setTimeout(loadStats, 5000);
    } catch (err) {
      alert(`Error starting benchmark: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setIsRunning(false);
    }
  };

  // Handle deleting results
  const handleDeleteResults = async () => {
    if (!deleteConfirm) {
      setDeleteConfirm(true);
      setTimeout(() => setDeleteConfirm(false), 3000); // Reset after 3 seconds
      return;
    }

    try {
      await deleteBenchmarkResults(benchmarkId);
      // Reload stats after deletion
      await loadStats();
      setDeleteConfirm(false);
    } catch (err) {
      alert(`Error deleting results: ${err instanceof Error ? err.message : 'Unknown error'}`);
    }
  };

  // Handle adding players
  const handleAddPlayers = async (players: PlayerConfig[]) => {
    try {
      setAddingPlayers(true);
      await addPlayersToBenchmark(benchmarkId, players);
      // Close modal and reload stats
      setShowAddPlayerModal(false);
      await loadStats();
    } catch (err) {
      alert(`Error adding players: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setAddingPlayers(false);
    }
  };

  // Get existing player IDs from config
  const getExistingPlayerIds = (): string[] => {
    if (!stats?.config?.players) return [];
    return stats.config.players.map((p: any) => p.id);
  };

  // Load initial data
  useEffect(() => {
    loadStats();
  }, [benchmarkId]);

  // Auto-refresh for running benchmarks (every 5 seconds)
  useEffect(() => {
    if (!stats || stats.status !== 'running') return;

    const interval = setInterval(loadStats, 5000);
    return () => clearInterval(interval);
  }, [stats?.status]);

  // Get available game names for tabs
  const gameNames = stats ? Object.keys(stats.per_game_scores) : [];

  if (loading && !stats) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading benchmark data...</p>
        </div>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md mx-auto">
          <div className="w-16 h-16 mx-auto mb-4 text-red-400">
            <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">Error Loading Benchmark</h3>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={loadStats}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors mr-2"
          >
            Retry
          </button>
          <button
            onClick={onBack}
            className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400 transition-colors"
          >
            Back to List
          </button>
        </div>
      </div>
    );
  }

  if (!stats) return null;

  const hasResults = stats.metadata.actual_results > 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <button
                onClick={onBack}
                className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors"
              >
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back to List
              </button>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Benchmark Dashboard</h1>
                <p className="text-sm text-gray-600">
                  {benchmarkId}
                </p>
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {stats.status === 'running' && (
                <span className="inline-flex items-center text-sm text-green-600">
                  <span className="animate-pulse w-2 h-2 bg-green-500 rounded-full mr-2"></span>
                  Live Updates
                </span>
              )}
              <button
                onClick={loadStats}
                disabled={loading}
                className="inline-flex items-center px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 transition-colors disabled:opacity-50"
              >
                <svg className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Management Panel - Always Visible */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
            {/* Progress and Status */}
            <div className="flex-1">
              <div className="flex items-center gap-4 mb-2">
                <span className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium ${
                  stats.status === 'completed'
                    ? 'bg-green-100 text-green-800'
                    : stats.status === 'running'
                    ? 'bg-yellow-100 text-yellow-800'
                    : 'bg-blue-100 text-blue-800'
                }`}>
                  {stats.status === 'completed' ? '✓ Completed' :
                   stats.status === 'running' ? '⏳ Running' : '🚀 Ready to Start'}
                </span>
                <span className="text-sm text-gray-600">
                  {stats.metadata.actual_results} / {stats.metadata.expected_results} results
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className={`h-2 rounded-full transition-all duration-500 ${
                    stats.status === 'completed' ? 'bg-green-600' :
                    stats.status === 'running' ? 'bg-blue-600' :
                    'bg-gray-400'
                  }`}
                  style={{ width: `${Math.min(100, (stats.metadata.actual_results / stats.metadata.expected_results) * 100)}%` }}
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2">
              <button
                onClick={handleRunBenchmark}
                disabled={isRunning || stats.status === 'running'}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  isRunning || stats.status === 'running' || stats.status === 'completed'
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-blue-600 text-white hover:bg-blue-700'
                }`}
              >
                {isRunning ? '⏳ Starting...' :
                 stats.status === 'ready' ? '🚀 Start Benchmark' :
                 stats.status === 'running' ? '⏳ Running...' :
                 stats.status === 'completed' ? '✅ Finished' :
                 '🚀 Continue Benchmark'}
              </button>

              <button
                onClick={() => setShowAddPlayerModal(true)}
                disabled={stats.status === 'running'}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  stats.status === 'running'
                    ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                    : 'bg-green-600 text-white hover:bg-green-700'
                }`}
              >
                ➕ Add Player
              </button>

              <button
                onClick={handleDeleteResults}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  deleteConfirm
                    ? 'bg-red-600 text-white hover:bg-red-700'
                    : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
                }`}
              >
                {deleteConfirm ? '⚠️ Confirm Delete?' : '🗑️ Delete Results'}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Configuration Section - Collapsible */}
      <div className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <button
            onClick={() => setConfigExpanded(!configExpanded)}
            className="w-full py-4 flex items-center justify-between text-left hover:bg-gray-50 transition-colors"
          >
            <div className="flex items-center gap-4">
              <h3 className="text-lg font-medium text-gray-900">Configuration</h3>
              <div className="flex gap-2 text-sm text-gray-600">
                <span className="px-2 py-1 bg-gray-100 rounded">
                  {stats.metadata.num_players} Player{stats.metadata.num_players !== 1 ? 's' : ''}
                </span>
                <span className="px-2 py-1 bg-gray-100 rounded">
                  {stats.metadata.num_games} Game{stats.metadata.num_games !== 1 ? 's' : ''}
                </span>
                <span className="px-2 py-1 bg-gray-100 rounded">
                  Judge: {stats.config?.metadata?.judge_model || 'N/A'}
                </span>
              </div>
            </div>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform ${configExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {configExpanded && (
            <div className="pb-4">
              <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
                <pre className="text-xs font-mono text-gray-700 whitespace-pre-wrap">
                  {JSON.stringify(stats.config, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <nav className="flex space-x-8" aria-label="Tabs">
            <button
              onClick={() => setCurrentView('overall')}
              className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                currentView === 'overall'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Overall
            </button>
            {gameNames.map((gameName) => (
              <button
                key={gameName}
                onClick={() => setCurrentView(gameName)}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  currentView === gameName
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {gameName}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentView === 'overall' ? (
          <OverallView stats={stats} />
        ) : (
          /* Game-specific view placeholder */
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              {currentView} - Detailed Analysis
            </h3>
            <p className="text-gray-600">
              Game-specific charts and analysis will be implemented in the next phase.
            </p>
          </div>
        )}
      </div>

      {/* Add Player Modal */}
      <Modal
        isOpen={showAddPlayerModal}
        onClose={() => setShowAddPlayerModal(false)}
        title="Add Players to Benchmark"
      >
        <PlayerConfigForm
          onSubmit={handleAddPlayers}
          onCancel={() => setShowAddPlayerModal(false)}
          existingPlayerIds={getExistingPlayerIds()}
          submitLabel={addingPlayers ? "Adding..." : "Add Players"}
        />
      </Modal>
    </div>
  );
}
