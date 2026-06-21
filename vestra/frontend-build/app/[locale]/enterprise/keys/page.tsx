'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Spinner, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import {
  Key, Copy, Trash2, Plus, Eye, EyeOff, Clock,
  AlertTriangle, ArrowLeft, CheckCircle2, X,
} from 'lucide-react';

interface ApiKey {
  id: number;
  name: string;
  key_prefix: string;
  scopes: string;
  rate_limit: number;
  is_active: boolean;
  last_used_at: string | null;
  created_at: string;
}

interface UsageStats {
  calls_today: number;
  calls_this_month: number;
  top_endpoints: { endpoint: string; calls: number }[];
}

const SCOPES_OPTIONS = [
  { value: 'read:properties', label: 'Read Properties' },
  { value: 'read:verifications', label: 'Read Verifications' },
  { value: 'read:analytics', label: 'Read Analytics' },
];

function ApiKeysContent() {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Create key modal state
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newScopes, setNewScopes] = useState<string[]>([]);
  const [newRateLimit, setNewRateLimit] = useState(1000);
  const [creating, setCreating] = useState(false);
  const [createdKey, setCreatedKey] = useState<string | null>(null);
  const [createError, setCreateError] = useState('');

  // Revoke confirmation
  const [revokingId, setRevokingId] = useState<number | null>(null);
  const [confirmRevoke, setConfirmRevoke] = useState<number | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [keysData, usageData] = await Promise.all([
        api.listApiKeys().catch(() => ({ keys: [] as ApiKey[] })),
        api.getApiKeyUsage().catch(() => null),
      ]);
      setKeys(keysData.keys || []);
      setUsage(usageData);
    } catch {
      setError('Failed to load API keys. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) {
      setCreateError('Please enter a key name.');
      return;
    }
    if (newScopes.length === 0) {
      setCreateError('Please select at least one scope.');
      return;
    }

    setCreating(true);
    setCreateError('');
    try {
      const result = await api.createApiKey(
        newName.trim(),
        newScopes.join(','),
        newRateLimit,
      );
      if (result.key) {
        setCreatedKey(result.key);
      }
    } catch {
      setCreateError('Failed to create API key. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (keyId: number) => {
    setRevokingId(keyId);
    try {
      await api.revokeApiKey(keyId);
      setKeys((prev) => prev.map((k) =>
        k.id === keyId ? { ...k, is_active: false } : k
      ));
    } catch {
      setError('Failed to revoke key. Please try again.');
    } finally {
      setRevokingId(null);
      setConfirmRevoke(null);
    }
  };

  const resetCreateForm = () => {
    setShowCreate(false);
    setNewName('');
    setNewScopes([]);
    setNewRateLimit(1000);
    setCreatedKey(null);
    setCreateError('');
  };

  const handleCopyKey = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      // Fallback — silently ignore clipboard errors
    }
  };

  const toggleScope = (scope: string) => {
    setNewScopes((prev) =>
      prev.includes(scope)
        ? prev.filter((s) => s !== scope)
        : [...prev, scope]
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex justify-center items-center py-32">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Link href="/enterprise" className="p-2 hover:bg-gray-100 rounded-xl transition-colors">
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </Link>
            <div>
              <h1 className="text-3xl font-bold text-gray-900">API Keys</h1>
              <p className="text-gray-500 text-sm mt-1">Manage your API keys and monitor usage</p>
            </div>
          </div>
          <Button onClick={() => setShowCreate(true)} className="gap-2">
            <Plus className="w-4 h-4" />
            Create New Key
          </Button>
        </div>

        {/* Error Banner */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl flex items-center gap-3 text-sm text-red-700">
            <AlertTriangle className="w-5 h-5 flex-shrink-0" />
            {error}
            <button onClick={() => setError('')} className="ml-auto p-1 hover:bg-red-100 rounded-lg transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Usage Stats */}
        {usage && (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <Card>
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-emerald-50 rounded-xl">
                  <Clock className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">Calls Today</p>
                  <p className="text-xl font-bold text-gray-900">
                    {usage.calls_today?.toLocaleString() || 0}
                  </p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-blue-50 rounded-xl">
                  <Key className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">Calls This Month</p>
                  <p className="text-xl font-bold text-gray-900">
                    {usage.calls_this_month?.toLocaleString() || 0}
                  </p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-purple-50 rounded-xl">
                  <Key className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">Active Keys</p>
                  <p className="text-xl font-bold text-gray-900">
                    {keys.filter((k) => k.is_active).length}
                  </p>
                </div>
              </div>
            </Card>
            <Card>
              <div className="flex items-center gap-3">
                <div className="p-2.5 bg-amber-50 rounded-xl">
                  <Key className="w-5 h-5 text-amber-600" />
                </div>
                <div>
                  <p className="text-xs text-gray-500">Total Keys</p>
                  <p className="text-xl font-bold text-gray-900">{keys.length}</p>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Create Key Modal */}
        {showCreate && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-xl border border-gray-100 w-full max-w-lg mx-4">
              {createdKey ? (
                <div className="p-8">
                  <div className="text-center mb-6">
                    <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                      <CheckCircle2 className="w-8 h-8 text-emerald-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-gray-900 mb-2">API Key Created</h2>
                    <p className="text-sm text-gray-500">
                      Copy this key now. You won&apos;t be able to see it again.
                    </p>
                  </div>
                  <div className="bg-gray-50 rounded-xl p-4 mb-4 relative">
                    <pre className="text-sm font-mono text-gray-800 break-all pr-8">{createdKey}</pre>
                    <button
                      onClick={() => handleCopyKey(createdKey)}
                      className="absolute top-3 right-3 p-1.5 bg-white rounded-lg border border-gray-200 hover:border-emerald-400 transition-colors"
                      title="Copy to clipboard"
                    >
                      <Copy className="w-4 h-4 text-gray-500" />
                    </button>
                  </div>
                  <div className="p-4 bg-amber-50 border border-amber-200 rounded-xl flex items-start gap-3 mb-6">
                    <AlertTriangle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <p className="text-sm text-amber-700 font-medium">
                      Store this key securely. It will NOT be shown again.
                    </p>
                  </div>
                  <Button fullWidth onClick={resetCreateForm}>
                    Done — Return to Keys
                  </Button>
                </div>
              ) : (
                <form onSubmit={handleCreateKey}>
                  <div className="p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h2 className="text-xl font-bold text-gray-900">Create New API Key</h2>
                      <button
                        type="button"
                        onClick={resetCreateForm}
                        className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                      >
                        <X className="w-5 h-5 text-gray-400" />
                      </button>
                    </div>

                    {createError && (
                      <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl flex items-center gap-2 text-sm text-red-700">
                        <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                        {createError}
                      </div>
                    )}

                    <div className="space-y-5">
                      <Input
                        label="Key Name"
                        value={newName}
                        onChange={(e) => setNewName(e.target.value)}
                        placeholder="e.g. Production API Key"
                        required
                      />

                      <div>
                        <label className="text-sm font-medium text-gray-700 mb-2 block">Scopes</label>
                        <div className="space-y-2">
                          {SCOPES_OPTIONS.map((scope) => (
                            <label
                              key={scope.value}
                              className="flex items-center gap-3 p-3 rounded-xl border border-gray-200 hover:border-emerald-300 cursor-pointer transition-colors"
                            >
                              <input
                                type="checkbox"
                                checked={newScopes.includes(scope.value)}
                                onChange={() => toggleScope(scope.value)}
                                className="w-4 h-4 rounded border-gray-300 text-emerald-600 focus:ring-emerald-500"
                              />
                              <span className="text-sm text-gray-700">{scope.label}</span>
                            </label>
                          ))}
                        </div>
                      </div>

                      <Input
                        label="Rate Limit (requests per day)"
                        type="number"
                        value={String(newRateLimit)}
                        onChange={(e) => setNewRateLimit(parseInt(e.target.value) || 1000)}
                        min={100}
                        max={100000}
                        required
                      />
                    </div>
                  </div>

                  <div className="p-6 pt-0 flex gap-3">
                    <Button type="button" variant="outline" fullWidth onClick={resetCreateForm}>
                      Cancel
                    </Button>
                    <Button type="submit" fullWidth loading={creating}>
                      <Plus className="w-4 h-4" />
                      Create Key
                    </Button>
                  </div>
                </form>
              )}
            </div>
          </div>
        )}

        {/* Keys List */}
        {keys.length === 0 ? (
          <Card className="text-center py-20 border-2 border-dashed border-gray-200">
            <Key className="w-16 h-16 text-gray-200 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No API keys yet</h3>
            <p className="text-gray-400 mb-6">Create your first API key to start integrating with the Vestra API.</p>
            <Button onClick={() => setShowCreate(true)} className="gap-2">
              <Plus className="w-4 h-4" />
              Create Your First Key
            </Button>
          </Card>
        ) : (
          <div className="space-y-4">
            {keys.map((key) => (
              <Card key={key.id} className="hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="font-semibold text-gray-900">{key.name}</h3>
                      <Badge variant={key.is_active ? 'success' : 'danger'}>
                        {key.is_active ? 'Active' : 'Revoked'}
                      </Badge>
                    </div>

                    <div className="flex items-center gap-2 mb-3">
                      <code className="text-sm font-mono bg-gray-50 px-3 py-1 rounded-lg text-gray-600 border border-gray-100">
                        {key.key_prefix}...
                      </code>
                      <button
                        onClick={() => handleCopyKey(key.key_prefix + '...')}
                        className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                        title="Copy key prefix"
                      >
                        <Copy className="w-4 h-4 text-gray-400" />
                      </button>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500">
                      <div className="flex items-center gap-1">
                        <Clock className="w-3.5 h-3.5" />
                        Created {new Date(key.created_at).toLocaleDateString()}
                      </div>
                      {key.last_used_at && (
                        <div className="flex items-center gap-1">
                          <Key className="w-3.5 h-3.5" />
                          Last used {new Date(key.last_used_at).toLocaleDateString()}
                        </div>
                      )}
                      <div className="flex items-center gap-1">
                        <Key className="w-3.5 h-3.5" />
                        {key.rate_limit?.toLocaleString() || '—'} req/day
                      </div>
                    </div>

                    {key.scopes && (
                      <div className="flex flex-wrap gap-1.5 mt-3">
                        {key.scopes.split(',').map((scope) => (
                          <span
                            key={scope}
                            className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full"
                          >
                            {scope.trim()}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="flex-shrink-0">
                    {key.is_active && (
                      <>
                        {confirmRevoke === key.id ? (
                          <div className="flex items-center gap-2">
                            <Button
                              size="sm"
                              variant="danger"
                              onClick={() => handleRevoke(key.id)}
                              loading={revokingId === key.id}
                            >
                              Confirm Revoke
                            </Button>
                            <button
                              onClick={() => setConfirmRevoke(null)}
                              className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                            >
                              <X className="w-4 h-4 text-gray-400" />
                            </button>
                          </div>
                        ) : (
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-red-200 text-red-600 hover:bg-red-50 hover:border-red-300"
                            onClick={() => setConfirmRevoke(key.id)}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                            Revoke
                          </Button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Top Endpoints */}
        {usage?.top_endpoints && usage.top_endpoints.length > 0 && (
          <div className="mt-10">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Top Endpoints</h2>
            <Card padding="none">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs font-semibold text-gray-400 uppercase border-b border-gray-100">
                      <th className="px-6 py-3">Endpoint</th>
                      <th className="px-6 py-3 text-right">Calls</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {usage.top_endpoints.map((ep, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="px-6 py-3">
                          <code className="text-sm font-mono text-gray-700">{ep.endpoint}</code>
                        </td>
                        <td className="px-6 py-3 text-right font-medium text-gray-900">
                          {ep.calls.toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ApiKeysPage() {
  return (
    <AuthGuard requireAuth>
      <ApiKeysContent />
    </AuthGuard>
  );
}
