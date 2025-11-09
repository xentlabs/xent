import { useEffect, useMemo, useState } from 'react';
import Modal from './Modal';
import { KeySummaryItem, getApiKeys, saveApiKeys, deleteApiKey } from '../utils/api';

const SUPPORTED_KEYS: string[] = [
  'OPENAI_API_KEY',
  'ANTHROPIC_API_KEY',
  'GEMINI_API_KEY',
  'GROK_API_KEY',
  'DEEPSEEK_API_KEY',
  'MOONSHOT_API_KEY',
  // Not a secret, but useful to set
  'OLLAMA_HOST',
];

interface ApiKeysModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ApiKeysModal({ isOpen, onClose }: ApiKeysModalProps) {
  const [summary, setSummary] = useState<KeySummaryItem[] | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [inputs, setInputs] = useState<Record<string, string>>({});

  const summaryByName = useMemo(() => {
    const map: Record<string, KeySummaryItem> = {};
    (summary || []).forEach((item) => { map[item.name] = item; });
    return map;
  }, [summary]);

  const refresh = async () => {
    try {
      setLoading(true);
      setError(null);
      const s = await getApiKeys();
      setSummary(s);
    } catch (e: any) {
      setError(e?.message || 'Failed to load API keys');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      // Reset inputs when opening
      setInputs({});
      refresh();
    }
  }, [isOpen]);

  const onChangeInput = (name: string, value: string) => {
    setInputs((prev) => ({ ...prev, [name]: value }));
  };

  const handleSave = async () => {
    const toSave: Record<string, string> = {};
    for (const k of SUPPORTED_KEYS) {
      const v = (inputs[k] || '').trim();
      if (v) {
        toSave[k] = v;
      }
    }
    if (Object.keys(toSave).length === 0) {
      onClose();
      return;
    }
    try {
      setSaving(true);
      setError(null);
      await saveApiKeys(toSave);
      setInputs({});
      await refresh();
    } catch (e: any) {
      setError(e?.message || 'Failed to save API keys');
    } finally {
      setSaving(false);
    }
  };

  const handleRemove = async (name: string) => {
    try {
      setSaving(true);
      setError(null);
      await deleteApiKey(name);
      const newInputs = { ...inputs };
      delete newInputs[name];
      setInputs(newInputs);
      await refresh();
    } catch (e: any) {
      setError(e?.message || 'Failed to delete API key');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="API Keys" maxWidth="900px">
      <div className="space-y-4">
        <p className="text-sm text-gray-600">
          Manage API keys used by model providers. Environment variables always override stored values.
        </p>

        {error && (
          <div className="p-3 rounded border border-red-300 bg-red-50 text-red-700 text-sm">{error}</div>
        )}

        {loading ? (
          <div className="text-gray-600 text-sm">Loading...</div>
        ) : (
          <div className="space-y-3">
            {SUPPORTED_KEYS.map((name) => {
              const item = summaryByName[name];
              const status = item?.set ? (item.source === 'env' ? 'Set via Environment' : 'Set via Keystore') : 'Not set';
              const last4 = item?.last4 ? `••••${item.last4}` : '';
              return (
                <div key={name} className="border border-gray-200 rounded p-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div className="flex-1 pr-0 md:pr-4 min-w-0">
                      <div className="font-mono text-sm text-gray-800 break-words">{name}</div>
                      <div className="text-xs text-gray-500 break-words">{status} {last4 && `(${last4})`}</div>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap md:flex-nowrap">
                      <input
                        type="text"
                        className="border border-gray-300 rounded px-2 py-1 text-sm w-full md:w-64"
                        placeholder={name === 'OLLAMA_HOST' ? 'e.g., http://localhost:11434' : 'Enter new value'}
                        value={inputs[name] || ''}
                        onChange={(e) => onChangeInput(name, e.target.value)}
                      />
                      <button
                        type="button"
                        className="px-3 py-1 text-sm rounded bg-blue-600 text-white hover:bg-blue-700"
                        onClick={handleSave}
                        disabled={saving}
                        title="Save any edited values"
                      >
                        Save
                      </button>
                      <button
                        type="button"
                        className="px-3 py-1 text-sm rounded bg-gray-200 text-gray-800 hover:bg-gray-300"
                        onClick={() => handleRemove(name)}
                        disabled={saving || !item || item.source === 'unset'}
                        title="Remove from keystore"
                      >
                        Remove
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            className="px-4 py-2 rounded bg-gray-200 text-gray-800 hover:bg-gray-300"
            onClick={onClose}
            disabled={saving}
          >
            Close
          </button>
        </div>
      </div>
    </Modal>
  );
}
