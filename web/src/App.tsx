import { useState, useEffect } from 'react';

type PlayerName = "black" | "white" | "alice" | "bob" | "carol" | "env";

interface PlayerConfig {
  name: PlayerName;
  id: string;
  player_type: string;
  options: {
    model?: string;
    provider?: string;
  };
}

interface GameConfig {
  name: string;
  code: string;
  presentation_function: string;
}

interface XegaMetadata {
  benchmark_id: string;
  xega_version: string;
  judge_model: string;
  num_rounds_per_game: number;
  seed: string;
}

interface ExpansionConfig {
  num_maps_per_game: number;
}

interface CondensedXegaBenchmarkConfig {
  config_type: "condensed_xega_config";
  metadata: XegaMetadata;
  expansion_config: ExpansionConfig;
  players: PlayerConfig[];
  games: GameConfig[];
}

const SIMPLE_GAME_CODE = `assign(s=story())
reveal(black, s)
elicit(black, x, 10)
assign(x1=remove_common_words(x, s)) # Remove any words in story from input text
reward(black, xed(s | x1))`;

const DEFAULT_PRESENTATION = `def present(state, history):
    """Default presentation matching current system output"""
    output = []
    for event in history:
        if event['type'] == 'elicit_request':
            output.append(format_elicit_request(event))
        elif event['type'] == 'elicit_response':
            output.append(format_elicit_response(event))
        elif event['type'] == 'reveal':
            output.append(format_reveal(event))
        elif event['type'] == 'reward':
            output.append(format_reward(event))
        elif event['type'] == 'failed_ensure':
            output.append(format_failed_ensure(event))
        else:
            # Fallback for unknown event types
            output.append(f"Unknown event: {event}")
    return '\\n'.join(output)`;

const SINGLE_PRESENTATION = `def present(state, history):
    story = state["s"]
    game_overview = f"""I am going to give you a short text. Your job is to provide a string that will prefix that text. Your goal is to minimize the cross-entropy of the text given the prefix you provide. You should respond with what will make the text as likely as possible.

The text is: "{story}"

Your response will be used as the prefix to that text and you will be scored on how well it helps predict that text. You may not use any words from the text in your response, regardless of case or punctuation. You can only use a maximum of 10 tokens for your prefix."""
    previous_attempts = []

    for event in history:
        if event["type"] == "elicit_response":
            previous_attempts.append("<attempt>")
            previous_attempts.append("You provided: " + event["response"])
        elif event["type"] == "reward":
            score = round(event["value"].total_xent(), 2)
            previous_attempts.append(f"Total score for that response: {score}")
            previous_attempts.append(
                f"Per token score for that response: {str(event['value'])}"
            )
            previous_attempts.append("</attempt>")

    if len(previous_attempts) == 0:
        instructions = "Provide your prefix inside of \`<move></move>\` tags. Any other text in your response will be ignored. You will be given feedback on your prefix and a chance to improve your prefix."
        output = [game_overview, "", instructions]
    else:
        instructions = "Use your previous attempts above to further optimize your prefix. Provide your prefix inside of \`<move></move>\` tags. Any other text in your response will be ignored."
        output = (
            [game_overview, "", "<previousAttempts>"]
            + previous_attempts
            + ["</previousAttempts>", "", instructions]
        )

    return "\\n".join(output)`;

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

function guessProviderFromModel(model: string): string {
  const modelLower = model.toLowerCase();
  if (modelLower.includes('gpt') || modelLower.includes('o3') || modelLower.includes('o4')) {
    return 'openai';
  } else if (modelLower.includes('claude')) {
    return 'anthropic';
  } else if (modelLower.includes('gemini')) {
    return 'gemini';
  } else if (modelLower.includes('grok')) {
    return 'grok';
  } else if (modelLower.includes('deepseek')) {
    return 'deepseek';
  } else if (model.includes('/') && !model.startsWith('ollama/')) {
    return 'openrouter';
  } else if (model.startsWith('ollama/')) {
    return 'ollama';
  } else {
    return 'openai'; // default fallback
  }
}

function App() {
  const [models, setModels] = useState<string[]>(['gpt-4o']);
  const [human, setHuman] = useState<boolean>(false);
  const [judge, setJudge] = useState<string>('gpt2');
  const [benchmarkId, setBenchmarkId] = useState<string>(generateBenchmarkId());
  const [seed, setSeed] = useState<string>('notrandom');
  const [numRoundsPerGame, setNumRoundsPerGame] = useState<number>(30);
  const [numMapsPerGame, setNumMapsPerGame] = useState<number>(1);
  const [useCustomGames, setUseCustomGames] = useState<boolean>(false);
  const [customGames, setCustomGames] = useState<GameConfig[]>([]);
  const [benchmarkIds, setBenchmarkIds] = useState<string[]>([]);
  const [loadingBenchmarks, setLoadingBenchmarks] = useState<boolean>(true);

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

  const buildConfig = (): CondensedXegaBenchmarkConfig => {
    let players: PlayerConfig[];
    if (!human) {
      players = models.map(model => ({
        name: "black" as PlayerName,
        id: model,
        player_type: "default",
        options: {
          model: model,
          provider: guessProviderFromModel(model),
        },
      }));
    } else {
      players = [{
        name: "black" as PlayerName,
        id: "human",
        player_type: "human",
        options: {},
      }];
    }

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
      config_type: "condensed_xega_config",
      metadata: {
        benchmark_id: benchmarkId,
        xega_version: "1.0.0", // This would be set by backend
        judge_model: judge,
        num_rounds_per_game: numRoundsPerGame,
        seed: seed,
      },
      expansion_config: {
        num_maps_per_game: numMapsPerGame,
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

  const addModel = () => {
    setModels(prev => [...prev, 'gpt-4o-mini']);
  };

  const removeModel = (index: number) => {
    setModels(prev => prev.filter((_, i) => i !== index));
  };

  const updateModel = (index: number, value: string) => {
    setModels(prev => prev.map((m, i) => i === index ? value : m));
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

  return (
    <div style={{ padding: '20px', fontFamily: 'system-ui, sans-serif', maxWidth: '800px', margin: '0 auto' }}>
      <h1>XEGA Benchmarks</h1>

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
                  onClick={() => console.log('View benchmark:', id)}
                  style={{ padding: '4px 12px', backgroundColor: '#007bff', color: 'white', border: 'none', borderRadius: '3px', cursor: 'pointer', fontSize: '12px' }}
                >
                  View
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      <hr style={{ margin: '30px 0', border: 'none', borderTop: '1px solid #dee2e6' }} />

      <h2>Create New Benchmark</h2>

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
          
          <div style={{ marginBottom: '15px' }}>
            <label>
              <input
                type="checkbox"
                checked={human}
                onChange={(e) => setHuman(e.target.checked)}
                style={{ marginRight: '10px' }}
              />
              Human Player (overrides models below)
            </label>
          </div>

          {!human && (
            <div>
              <h4>Model Players:</h4>
              {models.map((model, index) => (
                <div key={index} style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#f5f5f5' }}>
                  <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <input
                      type="text"
                      placeholder="Model name (e.g., gpt-4o, claude-3-sonnet)"
                      value={model}
                      onChange={(e) => updateModel(index, e.target.value)}
                      style={{ flex: 1, padding: '5px' }}
                    />
                    <span style={{ fontSize: '12px', color: '#666' }}>
                      Provider: {guessProviderFromModel(model)}
                    </span>
                    {models.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeModel(index)}
                        style={{ padding: '5px 10px', backgroundColor: '#ff4444', color: 'white', border: 'none', cursor: 'pointer' }}
                      >
                        Remove
                      </button>
                    )}
                  </div>
                </div>
              ))}

              <button
                type="button"
                onClick={addModel}
                style={{ padding: '5px 15px', backgroundColor: '#4CAF50', color: 'white', border: 'none', cursor: 'pointer' }}
              >
                Add Model
              </button>
            </div>
          )}

          {human && (
            <div style={{ padding: '10px', backgroundColor: '#e8f4fd', border: '1px solid #b3d9ff' }}>
              <strong>Human Player Mode</strong>
              <p style={{ margin: '5px 0', fontSize: '14px' }}>
                A single human player will be configured for interactive testing.
              </p>
            </div>
          )}
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
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Game Code (.xega DSL):</label>
                    <textarea
                      value={game.code}
                      onChange={(e) => updateCustomGame(index, 'code', e.target.value)}
                      style={{ width: '100%', padding: '10px', minHeight: '150px', fontFamily: 'monospace' }}
                      placeholder="Enter game logic using XEGA DSL..."
                    />
                  </div>

                  <div style={{ marginBottom: '10px' }}>
                    <label style={{ display: 'block', marginBottom: '5px', fontWeight: 'bold' }}>Presentation Function (Python):</label>
                    <textarea
                      value={game.presentation_function}
                      onChange={(e) => updateCustomGame(index, 'presentation_function', e.target.value)}
                      style={{ width: '100%', padding: '10px', minHeight: '150px', fontFamily: 'monospace' }}
                      placeholder="def present(state, history):..."
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
          It matches the output of <code>xega configure</code> CLI command.
        </p>
        <pre style={{ backgroundColor: 'white', padding: '10px', overflow: 'auto', maxHeight: '400px', fontSize: '12px' }}>
          {JSON.stringify(config, null, 2)}
        </pre>
      </div>
    </div>
  );
}

export default App;
