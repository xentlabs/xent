import { useState, useEffect } from 'react';
import BenchmarkDashboard from './views/BenchmarkDashboard';
import PlayerConfigForm, { PlayerConfig } from './components/PlayerConfigForm';
import PlayPage from './components/play/PlayPage';

interface GameConfig {
  name: string;
  code: string;
  presentation_function: string;
}

interface XentMetadata {
  benchmark_id: string;
  xent_version: string;
  judge_model: string;
  num_rounds_per_game: number;
  seed: string;
}

interface TextGenerationConfig {
  generator_type: "JUDGE" | "COMMUNITY_ARCHIVE"
  generator_config: any;
  max_length: number;
}

interface ExpansionConfig {
  num_maps_per_game: number;
  text_generation_config: TextGenerationConfig;
}

interface CondensedXentBenchmarkConfig {
  config_type: "condensed_xent_config";
  metadata: XentMetadata;
  expansion_config: ExpansionConfig;
  players: PlayerConfig[];
  games: GameConfig[];
}

const SIMPLE_GAME_CODE = `assign(s=story())
reveal(s)
elicit(x, 10)
assign(x1=remove_common_words(x, s)) # Remove any words in story from input text
reward(xed(s | x1))`;

const DEFAULT_PRESENTATION = `from typing import Any
from xent.presentation.sdk import (
    ChatBuilder,
    format_elicit_request,
    format_elicit_response,
    format_reveal,
    format_reward,
    format_failed_ensure,
)

def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    if ctx is None:
        ctx = {}

    b = ChatBuilder()

    # Send a one-time introduction/instructions
    if not ctx.get('intro_sent', False):
        b.user(
            "You are playing a text game. Provide your move inside <move></move> tags. Any other text will be ignored."
        )
        ctx['intro_sent'] = True

    # Summarize what happened since the last elicit
    for event in since_events:
        t = event.get('type')
        if t == 'elicit_request':
            b.user(format_elicit_request(event))
        elif t == 'elicit_response':
            b.user(format_elicit_response(event))
        elif t == 'reveal':
            b.user(format_reveal(event))
        elif t == 'reward':
            formatted, _ = format_reward(event)
            b.user("Score update:\\n" + str(formatted))
        elif t == 'failed_ensure':
            b.user(format_failed_ensure(event))
        else:
            b.user("Event: " + str(event))

    # Close with a concise instruction cue
    b.user("Now provide your next move inside <move></move> tags.")

    return b.render(), ctx`;

const SINGLE_PRESENTATION = `from xent.presentation.sdk import (
    ChatBuilder,
    PresentationBuilder,
    extract_reveals,
    extract_rewards,
    format_reward,
    get_max_score,
    split_rounds,
)


def present_turn(state, since_events, metadata, full_history=None, ctx=None):
    if ctx is None:
        ctx = {}

    history = full_history if full_history is not None else since_events
    rounds = split_rounds(history)
    all_rewards = extract_rewards(history)
    best_score, _ = get_max_score(all_rewards) if all_rewards else (None, None)

    b = ChatBuilder()

    # One-time header and story
    if not ctx.get("intro_sent", False):
        builder = PresentationBuilder()
        header = f"""You are playing a text game that uses the cross-entropy function of an LLM ({metadata["judge_model"]}) to compute score.

<gameCode>
assign(s=story())
elicit(x, 10)
assign(x1=remove_common_words(x, s))
reveal(x1)
reward(xed(s | x1))
</gameCode>

You will be given a short story, and your task is to provide a prefix that makes that story as predictable as possible. Think of it as providing context that helps predict what comes next.

The scoring measures how much information your prefix provides about the story. Specifically, your score is the difference between the story's baseline cross-entropy and its cross-entropy given your prefix: \`Score = crossEntropy(story) - crossEntropy(story | prefix)\`. Your goal is to maximize this score. So you want to find a prefix that will most help an LLM predict the story.

After each attempt, you'll see your score and a per-token breakdown of the cross entropy difference. The game automatically restarts after each successful attempt, allowing you to continuously optimize your approach. Use the feedback from previous rounds to improve your score.  Your final score is the maximum score you obtain over {metadata["num_rounds_per_game"]} rounds, so you should not worry about decreasing temporarily your score.

You cannot use any words that appear in the story itself (regardless of case or punctuation). Your prefix is limited to 10 tokens maximum.

Provide your prefix in <move></move> tags. Any other text in your response will be ignored."""

        builder.add_header(header)
        builder.add_line("")
        builder.add_line("The story:")
        builder.start_section("story")
        builder.add_line(str(state.get("s", "")))
        builder.end_section()
        if len(rounds) == 1:
            builder.add_line("First round starting.")
            builder.add_line("")
        builder.add_line("Provide your prefix in <move></move> tags.")
        b.user(builder.render())
        ctx["intro_sent"] = True
        return b.render(), ctx

    # Subsequent turns: summarize last completed round and prompt
    builder = PresentationBuilder()

    # Find the most recent completed round (with a reward)
    last_completed_index = None
    for i in range(len(rounds) - 1, -1, -1):
        if extract_rewards(rounds[i]):
            last_completed_index = i
            break

    if last_completed_index is not None:
        round_events = rounds[last_completed_index]
        rewards = extract_rewards(round_events)

        builder.add_line(f"Round {last_completed_index}:")

        # Show only the normalized prefix revealed
        reveals = extract_reveals(round_events)
        if reveals:
            prefix = reveals[0]["values"].get("x1")
            if prefix is not None:
                builder.add_line(f"<prefix>{prefix}</prefix>")

        # Score
        if rewards:
            builder.start_section("score")
            builder.add_lines(format_reward(rewards[0])[0])
            builder.end_section()

        builder.add_line("")

    if best_score is not None:
        builder.add_line(f"Best score achieved: {best_score:.3f}")

    builder.add_line("")
    builder.add_line("Remember: You want to maximize your score. Higher is better!")
    builder.add_line("")
    builder.add_line("Provide your prefix in <move></move> tags.")

    b.user(builder.render())
    return b.render(), ctx
  `;

function generateBenchmarkId(): string {
  const now = new Date();
  const dateStr = now.getFullYear() + '-' +
    String(now.getMonth() + 1).padStart(2, '0') + '-' +
    String(now.getDate()).padStart(2, '0') + '-' +
    String(now.getHours()).padStart(2, '0') + ':' +
    String(now.getMinutes()).padStart(2, '0') + ':' +
    String(now.getSeconds()).padStart(2, '0');
  const hashSuffix = Math.abs(now.getTime()).toString(16).slice(-6);
  return `${dateStr}-${hashSuffix}`;
}

function App() {
  const [players, setPlayers] = useState<PlayerConfig[]>([{
    name: 'black',
    id: 'gpt-4o',
    player_type: 'default',
    options: {
      model: 'gpt-4o',
      provider: 'openai',
    },
  }]);
  const [judge, setJudge] = useState<string>('gpt2');
  const [benchmarkId, setBenchmarkId] = useState<string>(generateBenchmarkId());
  const [seed, setSeed] = useState<string>('notrandom');
  const [numRoundsPerGame, setNumRoundsPerGame] = useState<number>(30);
  const [numMapsPerGame, setNumMapsPerGame] = useState<number>(1);
  const [useCustomGames, setUseCustomGames] = useState<boolean>(false);
  const [customGames, setCustomGames] = useState<GameConfig[]>([]);
  const [benchmarkIds, setBenchmarkIds] = useState<string[]>([]);
  const [loadingBenchmarks, setLoadingBenchmarks] = useState<boolean>(true);
  const [currentView, setCurrentView] = useState<'list' | 'dashboard' | 'play'>('list');
  const [selectedBenchmarkId, setSelectedBenchmarkId] = useState<string | null>(null);
  const [benchmarkResults, setBenchmarkResults] = useState<any>(null);
  const [loadingResults, setLoadingResults] = useState<boolean>(false);
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [deleteConfirm, setDeleteConfirm] = useState<boolean>(false);

  useEffect(() => {
    fetchBenchmarks();
  }, []);

  const fetchBenchmarks = async () => {
    try {
      setLoadingBenchmarks(true);
      const response = await fetch('/api/benchmarks');
      if (response.ok) {
        const ids = await response.json();
        setBenchmarkIds(ids);
      } else {
        console.error('Failed to fetch benchmarks');
      }
    } catch (error) {
      console.error('Error fetching benchmarks:', error);
    } finally {
      setLoadingBenchmarks(false);
    }
  };

  const buildConfig = (): CondensedXentBenchmarkConfig => {
    let games: GameConfig[];
    if (!useCustomGames || customGames.length === 0) {
      games = [{
        name: "simple_game",
        code: SIMPLE_GAME_CODE,
        presentation_function: SINGLE_PRESENTATION,
      }];
    } else {
      games = customGames;
    }

    return {
      config_type: "condensed_xent_config",
      metadata: {
        benchmark_id: benchmarkId,
        xent_version: "0.3.0",
        judge_model: judge,
        num_rounds_per_game: numRoundsPerGame,
        seed: seed,
      },
      expansion_config: {
        num_maps_per_game: numMapsPerGame,
        text_generation_config: {
          generator_type: "JUDGE",
          generator_config: {},
          max_length: 50,
        }
      },
      players: players,
      games: games,
    };
  };

  const config = buildConfig();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const response = await fetch('/api/config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ config }),
      });

      if (response.ok) {
        const result = await response.json();
        alert(`Configuration stored successfully!\nBenchmark ID: ${result.benchmark_id}`);
        fetchBenchmarks(); // Refresh the list
      } else {
        const error = await response.json();
        alert(`Error: ${error.detail || 'Failed to store configuration'}`);
      }
    } catch (error) {
      console.error('Network error:', error);
      alert('Network error: Could not connect to server');
    }
  };


  const addCustomGame = () => {
    setCustomGames(prev => [...prev, {
      name: 'New Game',
      code: SIMPLE_GAME_CODE,
      presentation_function: DEFAULT_PRESENTATION,
    }]);
  };

  const removeCustomGame = (index: number) => {
    setCustomGames(prev => prev.filter((_, i) => i !== index));
  };

  const updateCustomGame = (index: number, field: keyof GameConfig, value: string) => {
    setCustomGames(prev => prev.map((g, i) =>
      i === index ? { ...g, [field]: value } : g
    ));
  };

  const fetchBenchmarkResults = async (id: string) => {
    try {
      setLoadingResults(true);
      const response = await fetch(`/api/benchmarks/${id}`);
      if (response.ok) {
        const results = await response.json();
        setBenchmarkResults(results);
      } else if (response.status === 404) {
        setBenchmarkResults({ error: 'Benchmark not found or has no results yet' });
      } else {
        setBenchmarkResults({ error: 'Failed to fetch benchmark results' });
      }
    } catch (error) {
      console.error('Error fetching benchmark results:', error);
      setBenchmarkResults({ error: 'Network error fetching benchmark results' });
    } finally {
      setLoadingResults(false);
    }
  };

  const viewDashboard = (id: string) => {
    setSelectedBenchmarkId(id);
    setCurrentView('dashboard');
    setBenchmarkResults(null);
    setIsRunning(false);
    setDeleteConfirm(false);
  };

  const backToList = () => {
    setCurrentView('list');
    setSelectedBenchmarkId(null);
    setBenchmarkResults(null);
    setIsRunning(false);
    setDeleteConfirm(false);
  };

  const handleRunBenchmark = async () => {
    if (!selectedBenchmarkId || isRunning) return;

    try {
      setIsRunning(true);
      const response = await fetch(`/api/benchmarks/${selectedBenchmarkId}/run`, {
        method: 'POST',
      });

      if (response.ok) {
        const result = await response.json();
        // Keep the running state - don't disable it immediately
        // The benchmark is now running in the background
      } else {
        const error = await response.json();
        alert(`Error starting benchmark: ${error.detail || 'Unknown error'}`);
        setIsRunning(false);
      }
    } catch (error) {
      console.error('Network error:', error);
      alert('Network error: Could not start benchmark');
      setIsRunning(false);
    }
  };

  const handleDeleteResults = async () => {
    if (!selectedBenchmarkId) return;

    if (!deleteConfirm) {
      setDeleteConfirm(true);
      return;
    }

    try {
      const response = await fetch(`/api/benchmarks/${selectedBenchmarkId}/results`, {
        method: 'DELETE',
      });

      if (response.ok) {
        // Refresh the benchmark results after deletion
        await fetchBenchmarkResults(selectedBenchmarkId);
        setDeleteConfirm(false);
      } else {
        const error = await response.json();
        alert(`Error deleting results: ${error.detail || 'Unknown error'}`);
      }
    } catch (error) {
      console.error('Network error:', error);
      alert('Network error: Could not delete results');
    } finally {
      setDeleteConfirm(false);
    }
  };

  // Reset delete confirmation when clicking elsewhere
  useEffect(() => {
    const handleClickOutside = () => {
      if (deleteConfirm) {
        setDeleteConfirm(false);
      }
    };

    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, [deleteConfirm]);

  if (currentView === 'play') {
    return <PlayPage onBack={() => setCurrentView('list')} />;
  }

  if (currentView === 'dashboard' && selectedBenchmarkId) {
    return (
      <BenchmarkDashboard
        benchmarkId={selectedBenchmarkId}
        onBack={backToList}
      />
    );
  }

  return (
    <div style={{ padding: '20px', fontFamily: 'system-ui, sans-serif', maxWidth: '800px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h1>XENT Benchmarks</h1>
        <button
          onClick={() => setCurrentView('play')}
          style={{
            padding: '10px 20px',
            backgroundColor: '#9C27B0',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold'
          }}
        >
          🎮 Play Game
        </button>
      </div>

      {/* Benchmark List Section */}
      <div style={{ marginBottom: '30px', padding: '15px', backgroundColor: '#f8f9fa', borderRadius: '5px' }}>
        <h3>Saved Configurations</h3>
        {loadingBenchmarks ? (
          <p style={{ color: '#666' }}>Loading benchmarks...</p>
        ) : benchmarkIds.length === 0 ? (
          <p style={{ color: '#666' }}>No saved benchmarks yet. Create one below!</p>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {benchmarkIds.map((id) => (
              <li key={id} style={{ marginBottom: '8px', padding: '8px', backgroundColor: 'white', borderRadius: '3px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ fontFamily: 'monospace', fontSize: '14px' }}>{id}</span>
                <button
                  type="button"
                  onClick={() => viewDashboard(id)}
                  style={{ padding: '4px 12px', backgroundColor: '#3b82f6', color: 'white', border: 'none', borderRadius: '3px', cursor: 'pointer', fontSize: '12px' }}
                >
                  Dashboard
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <hr style={{ margin: '30px 0', border: 'none', borderTop: '1px solid #dee2e6' }} />

      <h1>Create New Benchmark</h1>

      <form onSubmit={handleSubmit} style={{ marginTop: '20px' }}>
        <fieldset style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ccc' }}>
          <legend><strong>Basic Settings</strong></legend>

          <div style={{ marginBottom: '10px' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>Judge Model:</label>
            <input
              type="text"
              value={judge}
              onChange={(e) => setJudge(e.target.value)}
              style={{ width: '100%', padding: '5px' }}
              placeholder="gpt2"
            />
          </div>

          <div style={{ marginBottom: '10px' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>Rounds per Game:</label>
            <input
              type="number"
              min="1"
              value={numRoundsPerGame}
              onChange={(e) => setNumRoundsPerGame(parseInt(e.target.value) || 1)}
              style={{ width: '100%', padding: '5px' }}
            />
          </div>

          <div style={{ marginBottom: '10px' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>Seed:</label>
            <input
              type="text"
              value={seed}
              onChange={(e) => setSeed(e.target.value || "notrandom")}
              style={{ width: '100%', padding: '5px' }}
              placeholder="notrandom"
            />
          </div>

          <div style={{ marginBottom: '10px' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>Benchmark ID:</label>
            <input
              type="text"
              value={benchmarkId}
              onChange={(e) => setBenchmarkId(e.target.value)}
              style={{ width: '100%', padding: '5px' }}
            />
            <button
              type="button"
              onClick={() => setBenchmarkId(generateBenchmarkId())}
              style={{ marginTop: '5px', padding: '5px 10px', fontSize: '12px' }}
            >
              Generate New ID
            </button>
          </div>

          <div style={{ marginBottom: '10px' }}>
            <label style={{ display: 'block', marginBottom: '5px' }}>Maps per Game:</label>
            <input
              type="number"
              min="1"
              value={numMapsPerGame}
              onChange={(e) => setNumMapsPerGame(parseInt(e.target.value) || 1)}
              style={{ width: '100%', padding: '5px' }}
            />
          </div>
        </fieldset>

        <fieldset style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ccc' }}>
          <legend><strong>Players</strong></legend>

          <PlayerConfigForm
            embedded={true}
            value={players}
            onChange={setPlayers}
          />
        </fieldset>

        <fieldset style={{ marginBottom: '20px', padding: '15px', border: '1px solid #ccc' }}>
          <legend><strong>Games</strong></legend>

          <div style={{ marginBottom: '15px' }}>
            <label>
              <input
                type="radio"
                name="gameType"
                checked={!useCustomGames}
                onChange={() => setUseCustomGames(false)}
                style={{ marginRight: '10px' }}
              />
              Use Default Simple Game
            </label>
            <div style={{ marginLeft: '25px', fontSize: '12px', color: '#666', marginTop: '5px' }}>
              A basic text completion game where players provide prefixes to minimize cross-entropy
            </div>
          </div>

          <div style={{ marginBottom: '15px' }}>
            <label>
              <input
                type="radio"
                name="gameType"
                checked={useCustomGames}
                onChange={() => setUseCustomGames(true)}
                style={{ marginRight: '10px' }}
              />
              Define Custom Games
            </label>
          </div>

          {useCustomGames && (
            <div>
              <h4>Custom Games:</h4>
              {customGames.map((game, index) => (
                <div key={index} style={{ marginBottom: '15px', padding: '15px', backgroundColor: '#f5f5f5', border: '1px solid #ddd' }}>
                  <div style={{ marginBottom: '10px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Game Name:</label>
                    <input
                      type="text"
                      value={game.name}
                      onChange={(e) => updateCustomGame(index, 'name', e.target.value)}
                      style={{ width: '100%', padding: '5px' }}
                      placeholder="e.g., my_custom_game"
                    />
                  </div>

                  <div style={{ marginBottom: '10px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Game Code (.xent DSL):</label>
                    <textarea
                      value={game.code}
                      onChange={(e) => updateCustomGame(index, 'code', e.target.value)}
                      style={{ width: '100%', padding: '10px', minHeight: '150px', fontFamily: 'monospace' }}
                      placeholder="Enter game logic using XENT DSL..."
                    />
                  </div>

                  <div style={{ marginBottom: '10px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Presentation Function (Python):</label>
                    <textarea
                      value={game.presentation_function}
                      onChange={(e) => updateCustomGame(index, 'presentation_function', e.target.value)}
                      style={{ width: '100%', padding: '10px', minHeight: '150px', fontFamily: 'monospace' }}
                      placeholder="def present(state, history, metadata):..."
                    />
                  </div>

                  <button
                    type="button"
                    onClick={() => removeCustomGame(index)}
                    style={{ padding: '5px 15px', backgroundColor: '#ff4444', color: 'white', border: 'none', cursor: 'pointer' }}
                  >
                    Remove Game
                  </button>
                </div>
              ))}

              <button
                type="button"
                onClick={addCustomGame}
                style={{ padding: '5px 15px', backgroundColor: '#4CAF50', color: 'white', border: 'none', cursor: 'pointer' }}
              >
                Add Custom Game
              </button>

              {customGames.length === 0 && (
                <div style={{ padding: '10px', backgroundColor: '#fff3cd', border: '1px solid #ffeaa7', marginTop: '10px' }}>
                  <strong>Note:</strong> No custom games defined. The default simple game will be used instead.
                </div>
              )}
            </div>
          )}

          {!useCustomGames && (
            <div style={{ padding: '10px', backgroundColor: '#e8f5e8', border: '1px solid #4CAF50', marginTop: '10px' }}>
              <strong>Default Simple Game</strong>
              <p style={{ margin: '5px 0', fontSize: '14px' }}>
                Game: "simple_game" - Players provide text prefixes to minimize cross-entropy of a generated story.
              </p>
            </div>
          )}
        </fieldset>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            type="submit"
            style={{ padding: '10px 20px', backgroundColor: '#2196F3', color: 'white', border: 'none', cursor: 'pointer', fontSize: '16px' }}
          >
            Create Benchmark Configuration
          </button>
        </div>
      </form>

      <div style={{ marginTop: '30px', padding: '15px', backgroundColor: '#f0f0f0', borderRadius: '5px' }}>
        <h3>Configuration Preview (JSON)</h3>
        <p style={{ fontSize: '12px', color: '#666', marginBottom: '10px' }}>
          This is the condensed configuration that will be sent to the backend.
          It matches the output of <code>xent configure</code> CLI command.
        </p>
        <pre style={{ backgroundColor: 'white', padding: '10px', overflow: 'auto', maxHeight: '400px', fontSize: '12px' }}>
          {JSON.stringify(config, null, 2)}
        </pre>
      </div>
    </div>
  );
}

export default App;
