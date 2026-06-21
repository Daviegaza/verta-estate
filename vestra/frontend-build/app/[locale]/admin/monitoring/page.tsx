'use client';

import { useEffect, useState, useCallback } from 'react';
import { Card, Spinner, Badge } from '@/components/ui/card';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import {
  Activity, Server, Database, Cpu, HardDrive, Wifi, WifiOff,
  AlertTriangle, CheckCircle, XCircle, Clock, RefreshCw,
  TrendingUp, Users, Building2, ShieldCheck, DollarSign,
  BarChart3, Zap, ArrowUpRight, ArrowDownRight, Thermometer,
} from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────────────────

interface ServiceStatus {
  name: string;
  status: 'up' | 'down' | 'degraded';
  latency_ms: number;
  message?: string;
}

interface ResourceMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  disk_percent: number;
  disk_free_gb: number;
  disk_total_gb: number;
}

interface SystemHealth {
  status: string;
  uptime_seconds: number;
  version: string;
  environment: string;
  timestamp: number;
}

interface FullHealth {
  system: SystemHealth;
  services: ServiceStatus[];
  resources: ResourceMetrics;
  api: { requests_per_minute: number; avg_latency_ms: number; p95_latency_ms: number; error_rate_5xx: number; error_rate_4xx: number; active_connections: number };
  business: { total_properties: number; total_users: number; total_verifications: number; total_payments_today: number; revenue_today_kes: number; pending_verifications: number; fraud_rate: number };
  recent_alerts: any[];
}

interface DBMetrics {
  active_connections: number;
  pool_size: number;
  max_overflow: number;
  tables: { name: string; size: string; rows: number }[];
}

interface RedisMetrics {
  uptime_days: number;
  connected_clients: number;
  used_memory_mb: number;
  hit_rate: number;
  ops_per_sec: number;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatUptime(seconds: number): string {
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function StatusDot({ status }: { status: string }) {
  const colors = { up: 'bg-emerald-500', down: 'bg-red-500', degraded: 'bg-amber-500' };
  return <span className={`inline-block w-2.5 h-2.5 rounded-full ${colors[status as keyof typeof colors] || 'bg-gray-400'} animate-pulse`} />;
}

function MetricGauge({ label, value, max, unit, color }: { label: string; value: number; max: number; unit: string; color: string }) {
  const pct = Math.min(100, (value / max) * 100);
  const colors: Record<string, string> = { emerald: 'bg-emerald-500', blue: 'bg-blue-500', amber: 'bg-amber-500', red: 'bg-red-500', purple: 'bg-purple-500' };
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-gray-500">{label}</span>
        <span className="font-semibold text-gray-900">{value}{unit}</span>
      </div>
      <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all duration-500 ${colors[color] || 'bg-emerald-500'}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────────────

export default function MonitoringDashboard() {
  const { user } = useAuthStore();
  const [health, setHealth] = useState<FullHealth | null>(null);
  const [dbMetrics, setDbMetrics] = useState<DBMetrics | null>(null);
  const [redisMetrics, setRedisMetrics] = useState<RedisMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchAll = useCallback(async () => {
    try {
      const [h, db, rds] = await Promise.all([
        api.getFullHealth().catch(() => null),
        api.getDatabaseMetrics().catch(() => null),
        api.getRedisMetrics().catch(() => null),
      ]);
      if (h) setHealth(h as unknown as FullHealth);
      if (db) setDbMetrics(db as unknown as DBMetrics);
      if (rds) setRedisMetrics(rds as unknown as RedisMetrics);
      setLastRefresh(new Date());
      setError('');
    } catch {
      setError('Failed to fetch monitoring data. Check if backend is running.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    if (!autoRefresh) return;
    const interval = setInterval(fetchAll, 10000);
    return () => clearInterval(interval);
  }, [fetchAll, autoRefresh]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center gap-3">
        <Spinner size="lg" />
        <span className="text-gray-500">Loading system monitoring...</span>
      </div>
    );
  }

  if (error && !health) {
    return (
      <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
        <AlertTriangle className="w-16 h-16 text-red-300" />
        <p className="text-red-600 font-medium">{error}</p>
        <button onClick={fetchAll} className="px-4 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 transition-colors">
          Retry
        </button>
      </div>
    );
  }

  const sysHealthy = health?.system.status === 'healthy';
  const allServicesUp = health?.services.every(s => s.status === 'up');

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-6 space-y-6">
        {/* ── Header ──────────────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-900 rounded-xl flex items-center justify-center">
              <Activity className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">System Monitoring</h1>
              <p className="text-sm text-gray-500">
                Real-time health • Last updated: {lastRefresh.toLocaleTimeString()}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={sysHealthy ? 'success' : 'danger'}>
              {sysHealthy ? <CheckCircle className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
              <span className="ml-1">{health?.system.status?.toUpperCase() || 'UNKNOWN'}</span>
            </Badge>
            <label className="flex items-center gap-1.5 text-xs text-gray-500 cursor-pointer select-none">
              <input type="checkbox" checked={autoRefresh} onChange={e => setAutoRefresh(e.target.checked)} className="w-3.5 h-3.5 rounded accent-emerald-600" />
              Auto
            </label>
            <button onClick={fetchAll} className="p-2 hover:bg-gray-100 rounded-lg transition-colors" title="Refresh now">
              <RefreshCw className="w-4 h-4 text-gray-500" />
            </button>
          </div>
        </div>

        {/* ── System Status Row ───────────────────────────────────────────── */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {health?.services.map(svc => (
            <Card key={svc.name} padding="sm" className={svc.status === 'up' ? '' : 'border-red-200 bg-red-50'}>
              <div className="flex items-center gap-3">
                <StatusDot status={svc.status} />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-gray-900 capitalize">{svc.name}</p>
                  <p className="text-xs text-gray-500">
                    {svc.status === 'up' ? `${svc.latency_ms}ms` : svc.message || 'Unreachable'}
                  </p>
                </div>
              </div>
            </Card>
          ))}
          <Card padding="sm">
            <div className="flex items-center gap-3">
              <div className={`w-2.5 h-2.5 rounded-full animate-pulse ${allServicesUp ? 'bg-emerald-500' : 'bg-red-500'}`} />
              <div>
                <p className="text-sm font-semibold text-gray-900">Overall</p>
                <p className="text-xs text-gray-500 capitalize">{health?.system.status || 'Unknown'}</p>
              </div>
            </div>
          </Card>
        </div>

        {/* ── Resource Metrics ────────────────────────────────────────────── */}
        {health?.resources && (
          <Card>
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Cpu className="w-4 h-4 text-gray-500" />
              System Resources
            </h3>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="space-y-4">
                <MetricGauge label="CPU" value={health.resources.cpu_percent} max={100} unit="%" color={health.resources.cpu_percent > 90 ? 'red' : health.resources.cpu_percent > 70 ? 'amber' : 'emerald'} />
                <MetricGauge label="Memory" value={health.resources.memory_percent} max={100} unit="%" color={health.resources.memory_percent > 90 ? 'red' : health.resources.memory_percent > 70 ? 'amber' : 'blue'} />
                <MetricGauge label="Disk" value={health.resources.disk_percent} max={100} unit="%" color={health.resources.disk_percent > 90 ? 'red' : health.resources.disk_percent > 70 ? 'amber' : 'purple'} />
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Memory Used</span><span className="font-semibold">{health.resources.memory_used_mb.toLocaleString()} MB / {health.resources.memory_total_mb.toLocaleString()} MB</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Disk Free</span><span className="font-semibold">{health.resources.disk_free_gb} GB / {health.resources.disk_total_gb} GB</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Uptime</span><span className="font-semibold">{formatUptime(health.system.uptime_seconds)}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Version</span><span className="font-semibold">v{health.system.version}</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Environment</span><Badge variant={health.system.environment === 'production' ? 'danger' : 'default'} className="text-xs">{health.system.environment}</Badge></div>
              </div>
            </div>
          </Card>
        )}

        {/* ── Database & Redis ────────────────────────────────────────────── */}
        <div className="grid lg:grid-cols-2 gap-4">
          {dbMetrics && (
            <Card>
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Database className="w-4 h-4 text-blue-500" />
                Database
              </h3>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="bg-blue-50 rounded-xl p-3 text-center">
                  <p className="text-xs text-blue-600 mb-0.5">Connections</p>
                  <p className="text-xl font-bold text-blue-900">{dbMetrics.active_connections}</p>
                  <p className="text-[10px] text-blue-400">of {dbMetrics.pool_size + dbMetrics.max_overflow}</p>
                </div>
                <div className="bg-purple-50 rounded-xl p-3 text-center">
                  <p className="text-xs text-purple-600 mb-0.5">Pool Size</p>
                  <p className="text-xl font-bold text-purple-900">{dbMetrics.pool_size}</p>
                  <p className="text-[10px] text-purple-400">+{dbMetrics.max_overflow} overflow</p>
                </div>
                <div className="bg-emerald-50 rounded-xl p-3 text-center">
                  <p className="text-xs text-emerald-600 mb-0.5">Tables</p>
                  <p className="text-xl font-bold text-emerald-900">{dbMetrics.tables.length}</p>
                </div>
              </div>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {dbMetrics.tables.slice(0, 8).map(t => (
                  <div key={t.name} className="flex items-center justify-between text-xs py-1.5 border-b border-gray-50">
                    <span className="text-gray-700 font-mono">{t.name}</span>
                    <span className="text-gray-400">{t.size} • {t.rows?.toLocaleString()} rows</span>
                  </div>
                ))}
              </div>
            </Card>
          )}
          {redisMetrics && (
            <Card>
              <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-500" />
                Redis Cache
              </h3>
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="bg-amber-50 rounded-xl p-3 text-center">
                  <p className="text-xs text-amber-600 mb-0.5">Hit Rate</p>
                  <p className="text-xl font-bold text-amber-900">{redisMetrics.hit_rate}%</p>
                </div>
                <div className="bg-emerald-50 rounded-xl p-3 text-center">
                  <p className="text-xs text-emerald-600 mb-0.5">Memory</p>
                  <p className="text-xl font-bold text-emerald-900">{redisMetrics.used_memory_mb}MB</p>
                </div>
                <div className="bg-purple-50 rounded-xl p-3 text-center">
                  <p className="text-xs text-purple-600 mb-0.5">Ops/sec</p>
                  <p className="text-xl font-bold text-purple-900">{redisMetrics.ops_per_sec.toLocaleString()}</p>
                </div>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-gray-500">Uptime</span><span className="font-semibold">{redisMetrics.uptime_days}d</span></div>
                <div className="flex justify-between"><span className="text-gray-500">Clients</span><span className="font-semibold">{redisMetrics.connected_clients}</span></div>
              </div>
            </Card>
          )}
        </div>

        {/* ── Business KPIs ───────────────────────────────────────────────── */}
        {health?.business && (
          <Card>
            <h3 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <BarChart3 className="w-4 h-4 text-gray-500" />
              Business Overview
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { label: 'Total Users', value: health.business.total_users.toLocaleString(), icon: <Users className="w-4 h-4" />, color: 'blue' },
                { label: 'Properties', value: health.business.total_properties.toLocaleString(), icon: <Building2 className="w-4 h-4" />, color: 'emerald' },
                { label: 'Verifications', value: health.business.total_verifications.toLocaleString(), icon: <ShieldCheck className="w-4 h-4" />, color: 'purple' },
                { label: 'Revenue Today', value: `KES ${(health.business.revenue_today_kes / 1000).toFixed(1)}K`, icon: <DollarSign className="w-4 h-4" />, color: 'amber' },
              ].map(kpi => (
                <div key={kpi.label} className="bg-gray-50 rounded-xl p-3">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${kpi.color === 'blue' ? 'bg-blue-100 text-blue-600' : kpi.color === 'emerald' ? 'bg-emerald-100 text-emerald-600' : kpi.color === 'purple' ? 'bg-purple-100 text-purple-600' : 'bg-amber-100 text-amber-600'}`}>
                    {kpi.icon}
                  </div>
                  <p className="text-xs text-gray-500">{kpi.label}</p>
                  <p className="text-lg font-bold text-gray-900">{kpi.value}</p>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* ── Alerts (from Alertmanager) ───────────────────────────────────── */}
        {health?.recent_alerts && health.recent_alerts.length > 0 && (
          <Card className="border-red-200">
            <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-500" />
              Active Alerts
            </h3>
            <div className="space-y-2">
              {health.recent_alerts.map((alert: any, i: number) => (
                <div key={i} className={`p-3 rounded-lg text-sm ${alert.severity === 'critical' ? 'bg-red-50 border border-red-200' : alert.severity === 'warning' ? 'bg-amber-50 border border-amber-200' : 'bg-blue-50 border border-blue-200'}`}>
                  <div className="flex items-center gap-2 mb-1">
                    <Badge variant={alert.severity === 'critical' ? 'danger' : 'warning'} className="text-[10px]">{alert.severity}</Badge>
                    <span className="font-semibold text-gray-900">{alert.name}</span>
                  </div>
                  <p className="text-xs text-gray-600">{alert.description}</p>
                </div>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
