'use client';

import { useState, useEffect } from 'react';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Spinner, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import type { Payment, PaymentStatus } from '@/types';
import {
  Wallet, ArrowDown, ArrowUp, Clock, CheckCircle, XCircle, ShieldCheck, Filter, Download
} from 'lucide-react';

interface PaymentSummary {
  totalSpent: number;
  pendingAmount: number;
  lastTransaction: string | null;
}

const STATUS_COLORS: Record<PaymentStatus, 'success' | 'warning' | 'info' | 'danger' | 'default'> = {
  completed: 'success',
  pending: 'warning',
  processing: 'info',
  failed: 'danger',
  refunded: 'default',
};

const STATUS_ICONS: Record<PaymentStatus, React.ReactNode> = {
  completed: <CheckCircle className="w-3.5 h-3.5" />,
  pending: <Clock className="w-3.5 h-3.5" />,
  processing: <Clock className="w-3.5 h-3.5" />,
  failed: <XCircle className="w-3.5 h-3.5" />,
  refunded: <ArrowDown className="w-3.5 h-3.5" />,
};

function formatKES(amount: number): string {
  return `KES ${amount.toLocaleString('en-KE')}`;
}

function formatPaymentDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-KE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function getMethodBadge(method: string): { label: string; variant: 'default' | 'success' | 'info' | 'purple' } {
  switch (method) {
    case 'mpesa': return { label: 'M-Pesa', variant: 'success' };
    case 'stripe': return { label: 'Stripe', variant: 'info' };
    case 'bank_transfer': return { label: 'Bank Transfer', variant: 'purple' };
    default: return { label: method, variant: 'default' };
  }
}

function getPurposeLabel(purpose: string): string {
  return purpose
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function WalletPage() {
  return (
    <AuthGuard requireAuth>
      <WalletContent />
    </AuthGuard>
  );
}

function WalletContent() {
  const { user } = useAuthStore();
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState<PaymentStatus | 'all'>('all');

  useEffect(() => {
    loadPayments();
  }, []);

  const loadPayments = async () => {
    try {
      setError('');
      const data = await api.getMyPayments();
      setPayments(data || []);
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to load payment history');
    } finally {
      setLoading(false);
    }
  };

  const filteredPayments = statusFilter === 'all'
    ? payments
    : payments.filter((p) => p.status === statusFilter);

  const summary: PaymentSummary = {
    totalSpent: payments
      .filter((p) => p.status === 'completed')
      .reduce((sum, p) => sum + p.amount, 0),
    pendingAmount: payments
      .filter((p) => p.status === 'pending' || p.status === 'processing')
      .reduce((sum, p) => sum + p.amount, 0),
    lastTransaction: payments.length > 0
      ? payments[0].created_at
      : null,
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <div className="p-3 bg-emerald-100 rounded-2xl">
            <Wallet className="w-6 h-6 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Wallet &amp; Payments</h1>
            <p className="text-sm text-gray-500">Track your spending and payment history</p>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl text-sm text-red-700 flex items-start gap-2">
            <XCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <div className="flex-1">{error}</div>
            <button
              onClick={loadPayments}
              className="text-red-700 underline font-medium hover:text-red-800 text-xs"
            >
              Retry
            </button>
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <div className="flex justify-center py-32">
            <Spinner size="lg" />
          </div>
        ) : payments.length === 0 ? (
          /* Empty state */
          <Card className="text-center py-24 border-2 border-dashed border-gray-200 bg-white/50">
            <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Wallet className="w-8 h-8 text-gray-300" />
            </div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No payments yet</h3>
            <p className="text-gray-400 text-sm mb-6 max-w-sm mx-auto">
              Your payment history will appear here once you make your first transaction. Start by verifying a property for just KES 500.
            </p>
            <div className="flex flex-wrap gap-3 justify-center">
              <a href="/verify">
                <Button className="gap-2">
                  <ShieldCheck className="w-4 h-4" />
                  Verify a Property — KES 500
                </Button>
              </a>
              <a href="/market">
                <Button variant="outline">
                  Browse Properties
                </Button>
              </a>
            </div>
          </Card>
        ) : (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
              <Card>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Total Spent</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1.5">
                      {formatKES(summary.totalSpent)}
                    </p>
                    {summary.lastTransaction && (
                      <p className="text-xs text-gray-400 mt-1">
                        Last: {formatPaymentDate(summary.lastTransaction)}
                      </p>
                    )}
                  </div>
                  <div className="p-3 bg-emerald-50 rounded-xl">
                    <ArrowUp className="w-5 h-5 text-emerald-600" />
                  </div>
                </div>
              </Card>

              <Card>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Pending</p>
                    <p className="text-2xl font-bold text-amber-600 mt-1.5">
                      {formatKES(summary.pendingAmount)}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      {payments.filter((p) => p.status === 'pending' || p.status === 'processing').length} transactions
                    </p>
                  </div>
                  <div className="p-3 bg-amber-50 rounded-xl">
                    <Clock className="w-5 h-5 text-amber-600" />
                  </div>
                </div>
              </Card>

              <Card>
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-xs text-gray-500 font-medium uppercase tracking-wider">Transactions</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1.5">
                      {payments.length}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Total payments
                    </p>
                  </div>
                  <div className="p-3 bg-blue-50 rounded-xl">
                    <Wallet className="w-5 h-5 text-blue-600" />
                  </div>
                </div>
              </Card>
            </div>

            {/* Filter & Download */}
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-gray-900">Payment History</h2>
              <div className="flex items-center gap-3">
                <div className="relative">
                  <Filter className="w-4 h-4 text-gray-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value as PaymentStatus | 'all')}
                    className="pl-9 pr-4 py-2 bg-white border border-gray-200 rounded-xl text-sm text-gray-700 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 appearance-none cursor-pointer"
                  >
                    <option value="all">All Payments</option>
                    <option value="completed">Completed</option>
                    <option value="pending">Pending</option>
                    <option value="failed">Failed</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Payment Table */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-gray-100 bg-gray-50/50">
                      <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Date</th>
                      <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Amount</th>
                      <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Method</th>
                      <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Purpose</th>
                      <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Status</th>
                      <th className="text-left text-xs font-semibold text-gray-500 uppercase tracking-wider px-5 py-3">Reference</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {filteredPayments.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-5 py-12 text-center text-gray-400 text-sm">
                          No payments match the selected filter.
                        </td>
                      </tr>
                    ) : (
                      filteredPayments.map((payment) => {
                        const methodBadge = getMethodBadge(payment.method);
                        return (
                          <tr key={payment.id} className="hover:bg-gray-50/50 transition-colors">
                            <td className="px-5 py-3.5 text-sm text-gray-700 whitespace-nowrap">
                              {formatPaymentDate(payment.created_at)}
                            </td>
                            <td className="px-5 py-3.5 text-sm font-semibold text-gray-900 whitespace-nowrap">
                              {formatKES(payment.amount)}
                            </td>
                            <td className="px-5 py-3.5 whitespace-nowrap">
                              <Badge variant={methodBadge.variant}>{methodBadge.label}</Badge>
                            </td>
                            <td className="px-5 py-3.5 text-sm text-gray-700 whitespace-nowrap">
                              {getPurposeLabel(payment.purpose)}
                            </td>
                            <td className="px-5 py-3.5 whitespace-nowrap">
                              <Badge
                                variant={STATUS_COLORS[payment.status]}
                                className="inline-flex items-center gap-1"
                              >
                                {STATUS_ICONS[payment.status]}
                                {payment.status}
                              </Badge>
                            </td>
                            <td className="px-5 py-3.5 text-sm text-gray-400 font-mono whitespace-nowrap">
                              {payment.reference || payment.mpesa_checkout_request_id || '—'}
                            </td>
                          </tr>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Download prompt */}
            <div className="mt-6 flex items-center justify-between p-4 bg-emerald-50 border border-emerald-200 rounded-2xl">
              <div className="flex items-center gap-3">
                <Download className="w-4 h-4 text-emerald-600" />
                <p className="text-sm text-emerald-700">
                  Download your complete payment history for records or accounting.
                </p>
              </div>
              <Button variant="outline" size="sm" className="flex-shrink-0 whitespace-nowrap">
                Export CSV
              </Button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
