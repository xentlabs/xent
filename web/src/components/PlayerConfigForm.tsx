import { useState } from 'react';
import { parseModelSpec } from '../utils/modelSpec';

export interface PlayerConfig {
  name: 'black' | 'white' | 'alice' | 'bob' | 'carol' | 'env';
  id: string;
  player_type: string;
  options: {
    model?: string;
    provider?: string;
    request_params?: any;
  };
}

interface PlayerConfigFormProps {
  onSubmit?: (players: PlayerConfig[]) => void;
  onCancel?: () => void;
  existingPlayerIds?: string[];
  submitLabel?: string;
  embedded?: boolean; // For embedding in another form
  value?: PlayerConfig[]; // Controlled component support
  onChange?: (players: PlayerConfig[]) => void; // For controlled mode
}

function guessProviderFromModel(model: string): string {
  const modelLower = model.toLowerCase().trim();
  // Detect Ollama models first: either explicit namespace or tag syntax like "qwen2:7b"
  if (modelLower.startsWith('ollama/') || modelLower.includes(':')) {
    return 'ollama';
  }
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
  } else if (model.includes('/') && !modelLower.startsWith('ollama/')) {
    // Likely an OpenRouter or HF-style identifier; keep previous behavior here
    return 'openrouter';
  } else {
    return 'openai'; // default fallback
  }
}

export default function PlayerConfigForm({
  onSubmit,
  onCancel,
  existingPlayerIds = [],
  submitLabel = 'Add Players',
  embedded = false,
  value,
  onChange
}: PlayerConfigFormProps) {
  // Initialize state from value prop if provided
  const initModels = () => {
    if (value && value.length > 0) {
      if (value[0].player_type === 'human') {
        return [];
      }
      return value.map(p => p.id);
    }
    return ['gpt-4o-mini'];
  };

  const initIsHuman = (): boolean => {
    return !!(value && value.length > 0 && value[0].player_type === 'human');
  };

  const [models, setModels] = useState<string[]>(initModels());
  const [isHuman, setIsHuman] = useState<boolean>(initIsHuman());
  const [error, setError] = useState<string | null>(null);

  // Helper to build player configs from current state
  const buildPlayerConfigs = (currentModels: string[], currentIsHuman: boolean): PlayerConfig[] => {
    if (currentIsHuman) {
      return [{
        name: 'black',
        id: 'human',
        player_type: 'human',
        options: {},
      }];
    }
    return currentModels.map(spec => {
      const { model, params } = parseModelSpec(spec);
      const player: PlayerConfig = {
        name: 'black' as const,
        id: model,
        player_type: 'default',
        options: {
          model,
          provider: guessProviderFromModel(model),
        },
      };
      if (params && Object.keys(params).length > 0) {
        (player.options as any).request_params = params;
      }
      return player;
    });
  };

  // Notify parent of changes in embedded mode
  const notifyChange = (newModels: string[], newIsHuman: boolean) => {
    if (embedded && onChange) {
      const players = buildPlayerConfigs(newModels, newIsHuman);
      onChange(players);
    }
  };

  const addModel = () => {
    const newModels = [...models, 'gpt-4o-mini'];
    setModels(newModels);
    notifyChange(newModels, isHuman);
  };

  const removeModel = (index: number) => {
    const newModels = models.filter((_, i) => i !== index);
    setModels(newModels);
    notifyChange(newModels, isHuman);
  };

  const updateModel = (index: number, value: string) => {
    const newModels = models.map((m, i) => i === index ? value : m);
    setModels(newModels);
    setError(null); // Clear error when user makes changes
    notifyChange(newModels, isHuman);
  };

  const updateIsHuman = (value: boolean) => {
    setIsHuman(value);
    setError(null);
    notifyChange(models, value);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    // Skip if embedded (parent form handles submission)
    if (embedded) return;

    // Build player configs
    let players: PlayerConfig[];
    if (isHuman) {
      // Check if human player already exists
      if (existingPlayerIds.includes('human')) {
        setError('A human player already exists in this benchmark');
        return;
      }
      players = buildPlayerConfigs(models, true);
    } else {
      // Validate models
      const duplicates = models
        .map(spec => parseModelSpec(spec).model)
        .filter(base => existingPlayerIds.includes(base));
      if (duplicates.length > 0) {
        setError(`These models already exist in the benchmark: ${duplicates.join(', ')}`);
        return;
      }

      // Check for empty model names
      if (models.some(m => !m.trim())) {
        setError('All model names must be filled in');
        return;
      }

      players = buildPlayerConfigs(models, false);
    }

    if (onSubmit) {
      onSubmit(players);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {error && (
        <div style={{
          marginBottom: '15px',
          padding: '10px',
          backgroundColor: '#fee',
          border: '1px solid #fcc',
          borderRadius: '4px',
          color: '#c00'
        }}>
          {error}
        </div>
      )}

      <div style={{ marginBottom: '20px' }}>
        <label style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
          <input
            type="checkbox"
            checked={isHuman}
            onChange={(e) => updateIsHuman(e.target.checked)}
            style={{ marginRight: '10px' }}
          />
          <span>{embedded ? 'Human Player' : 'Add Human Player'}</span>
        </label>

        {!isHuman ? (
          <div>
            <h4 style={{ marginBottom: '10px' }}>Model Players</h4>
            {models.map((model, index) => (
              <div key={index} style={{
                marginBottom: '10px',
                padding: '10px',
                backgroundColor: '#f5f5f5',
                borderRadius: '4px'
              }}>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <input
                    type="text"
                    placeholder="Model name (e.g., gpt-4o, claude-3-sonnet)"
                    value={model}
                    onChange={(e) => updateModel(index, e.target.value)}
                    style={{
                      flex: 1,
                      padding: '8px',
                      border: '1px solid #ddd',
                      borderRadius: '4px'
                    }}
                    required
                  />
                  <span style={{ fontSize: '12px', color: '#666', minWidth: '80px' }}>
                    {guessProviderFromModel(parseModelSpec(model).model)}
                  </span>
                  {models.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeModel(index)}
                      style={{
                        padding: '6px 12px',
                        backgroundColor: '#ff4444',
                        color: 'white',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer'
                      }}
                    >
                      Remove
                    </button>
                  )}
                </div>
              </div>
            ))}

            <div style={{ marginTop: '6px', fontSize: '12px', color: '#666' }}>
              Tip: add query params like <code>?temperature=0.7&amp;reasoning_effort="high"</code>
            </div>

            <button
              type="button"
              onClick={addModel}
              style={{
                padding: '8px 16px',
                backgroundColor: '#4CAF50',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                marginTop: '10px'
              }}
            >
              + Add Another Model
            </button>
          </div>
        ) : (
          <div style={{
            padding: '15px',
            backgroundColor: '#e8f4fd',
            border: '1px solid #b3d9ff',
            borderRadius: '4px'
          }}>
            <strong>Human Player Mode</strong>
            <p style={{ margin: '5px 0', fontSize: '14px' }}>
              A human player will be added for interactive testing.
            </p>
          </div>
        )}
      </div>

      {existingPlayerIds.length > 0 && (
        <div style={{
          marginBottom: '20px',
          padding: '10px',
          backgroundColor: '#f8f9fa',
          borderRadius: '4px'
        }}>
          <strong>Existing Players:</strong>
          <div style={{ marginTop: '5px' }}>
            {existingPlayerIds.map(id => (
              <span key={id} style={{
                display: 'inline-block',
                marginRight: '8px',
                marginTop: '4px',
                padding: '4px 8px',
                backgroundColor: '#e9ecef',
                borderRadius: '3px',
                fontSize: '12px'
              }}>
                {id}
              </span>
            ))}
          </div>
        </div>
      )}

      {!embedded && (
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button
            type="button"
            onClick={onCancel}
            style={{
              padding: '10px 20px',
              backgroundColor: '#6c757d',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            Cancel
          </button>
          <button
            type="submit"
            style={{
              padding: '10px 20px',
              backgroundColor: '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer'
            }}
          >
            {submitLabel}
          </button>
        </div>
      )}
    </form>
  );
}
