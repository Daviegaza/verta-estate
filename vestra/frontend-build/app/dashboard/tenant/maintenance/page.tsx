'use client';

import { useState } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/card';
import api from '@/lib/api';
import {
  Wrench, ArrowLeft, Plus, AlertCircle, CheckCircle,
  Clock, FileText
} from 'lucide-react';

export default function TenantMaintenancePage() {
  return (
    <AuthGuard requireAuth requireRoles={['tenant']}>
      <MaintenanceContent />
    </AuthGuard>
  );
}

function MaintenanceContent() {
  const [issue, setIssue] = useState('');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [requests, setRequests] = useState<any[]>([]);

  // Load existing maintenance requests
  useState(() => {
    api.client.get('/api/rentals/maintenance')
      .then(r => setRequests(r.data || r.data?.items || []))
      .catch(() => {});
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!issue.trim()) return;
    setSubmitting(true);
    try {
      await api.client.post('/api/rentals/maintenance', {
        issue,
        description,
      });
      setSubmitted(true);
      setIssue('');
      setDescription('');
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to submit request');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center gap-3 mb-2">
        <Link href="/dashboard/tenant" className="p-2 hover:bg-gray-100 rounded-xl">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Maintenance Requests</h1>
          <p className="text-sm text-gray-500">Report issues with your rental unit</p>
        </div>
      </div>

      {submitted && (
        <Card padding="md" className="bg-emerald-50 border-emerald-200">
          <div className="flex items-center gap-3">
            <CheckCircle className="w-6 h-6 text-emerald-600" />
            <div>
              <p className="font-semibold text-emerald-800">Request Submitted!</p>
              <p className="text-sm text-emerald-600">Your landlord has been notified.</p>
            </div>
          </div>
        </Card>
      )}

      <Card padding="md">
        <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
          <Wrench className="w-5 h-5 text-amber-600" />
          Submit New Request
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Issue</label>
            <select
              value={issue}
              onChange={e => setIssue(e.target.value)}
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-amber-500 focus:border-transparent"
              required
            >
              <option value="">Select issue type...</option>
              <option value="plumbing">Plumbing — Leaks, clogs, water issues</option>
              <option value="electrical">Electrical — Power, lights, sockets</option>
              <option value="structural">Structural — Walls, roof, floors</option>
              <option value="appliance">Appliance — Fridge, stove, etc.</option>
              <option value="pest">Pest Control — Insects, rodents</option>
              <option value="security">Security — Locks, doors, windows</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              rows={4}
              placeholder="Describe the issue in detail..."
              className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-amber-500 focus:border-transparent resize-none"
            />
          </div>
          <Button
            type="submit"
            loading={submitting}
            className="w-full gap-2 bg-amber-600 hover:bg-amber-500"
          >
            <Plus className="w-4 h-4" /> Submit Request
          </Button>
        </form>
      </Card>

      {/* Previous Requests */}
      <Card padding="none">
        <div className="px-5 pt-4 pb-3">
          <h3 className="font-bold text-gray-900 flex items-center gap-2">
            <FileText className="w-5 h-5 text-amber-600" />
            Previous Requests
          </h3>
        </div>
        {requests.length === 0 ? (
          <div className="text-center py-10 px-4">
            <Wrench className="w-10 h-10 text-gray-200 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No maintenance requests yet.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-50 px-5 pb-4">
            {requests.map((req: any) => (
              <div key={req.id} className="flex items-center justify-between py-3">
                <div>
                  <p className="text-sm font-semibold text-gray-900 capitalize">{req.issue || req.title}</p>
                  <p className="text-xs text-gray-500">{req.description?.slice(0, 80) || 'No description'}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{new Date(req.created_at).toLocaleDateString()}</p>
                </div>
                <Badge variant={
                  req.status === 'resolved' ? 'success' :
                  req.status === 'in_progress' ? 'info' :
                  'warning'
                } className="text-xs">
                  {req.status?.replace(/_/g, ' ') || 'Pending'}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  );
}
