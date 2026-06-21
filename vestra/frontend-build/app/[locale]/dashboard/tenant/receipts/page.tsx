'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import {
  ArrowLeft, FileText, Download, CheckCircle, Clock, DollarSign,
  Calendar, Home, Phone, Shield, Printer, Share2
} from 'lucide-react';

interface ReceiptItem {
  id: number;
  receipt_number: string;
  tenant_name: string;
  unit_name: string;
  building?: string;
  amount_paid: number;
  rent_amount: number;
  late_fee: number;
  month: string;
  paid_date: string;
  mpesa_ref?: string;
  landlord_name: string;
  status: string;
}

export default function ReceiptsPage() {
  return (
    <AuthGuard requireAuth requireRoles={['tenant']}>
      <ReceiptsContent />
    </AuthGuard>
  );
}

function ReceiptsContent() {
  const [payments, setPayments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedReceipt, setSelectedReceipt] = useState<any | null>(null);

  useEffect(() => {
    api.client.get('/api/payments/my')
      .then(r => {
        const rentPayments = (r.data || []).filter((p: any) =>
          p.purpose === 'rent' || (p.description || '').toLowerCase().includes('rent')
        );
        setPayments(rentPayments);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex justify-center py-32"><Spinner size="lg" /></div>
  );

  // Detail view
  if (selectedReceipt) return (
    <ReceiptDetail
      receipt={selectedReceipt}
      onBack={() => setSelectedReceipt(null)}
    />
  );

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard/tenant" className="p-2 hover:bg-gray-100 rounded-xl">
            <ArrowLeft className="w-5 h-5 text-gray-500" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">My Receipts</h1>
            <p className="text-sm text-gray-500">{payments.length} digital receipt{payments.length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        <Button variant="outline" className="gap-2" onClick={() => window.print()}>
          <Printer className="w-4 h-4" /> Print All
        </Button>
      </div>

      {payments.length === 0 ? (
        <Card className="text-center py-20">
          <FileText className="w-16 h-16 text-gray-200 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-700 mb-2">No Receipts Yet</h2>
          <p className="text-gray-500 mb-6">Receipts are auto-generated when you pay rent. All your receipts will appear here forever.</p>
          <Link href="/dashboard/tenant/rent">
            <Button className="gap-2 bg-orange-600 hover:bg-orange-500">
              <DollarSign className="w-4 h-4" /> Pay Rent Now
            </Button>
          </Link>
        </Card>
      ) : (
        <div className="space-y-3">
          {payments.map(p => (
            <div
              key={p.id}
              onClick={() => setSelectedReceipt({
                id: p.id,
                receipt_number: `RCP-${String(p.id).padStart(6, '0')}`,
                amount_paid: p.amount,
                month: new Date(p.created_at).toLocaleDateString('en-KE', { month: 'long', year: 'numeric' }),
                paid_date: new Date(p.created_at).toLocaleDateString('en-KE', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric', hour: '2-digit', minute: '2-digit' }),
                mpesa_ref: p.mpesa_receipt_number || p.reference || '',
                status: p.status,
                landlord_name: 'Landlord',
              })}
              className="cursor-pointer"
            >
              <Card padding="md" className="hover:shadow-md hover:border-orange-200 transition-all group">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className={`w-12 h-12 rounded-2xl flex items-center justify-center ${
                      p.status === 'completed' ? 'bg-emerald-100' : 'bg-amber-100'
                    }`}>
                      {p.status === 'completed' ? (
                        <CheckCircle className="w-6 h-6 text-emerald-600" />
                      ) : (
                        <Clock className="w-6 h-6 text-amber-600" />
                      )}
                    </div>
                    <div>
                      <div className="flex items-center gap-2 mb-0.5">
                        <h3 className="font-bold text-gray-900 group-hover:text-orange-700 transition-colors">
                          Receipt #RCP-{String(p.id).padStart(6, '0')}
                        </h3>
                        <Badge variant={p.status === 'completed' ? 'success' : 'warning'} className="text-xs">
                          {p.status === 'completed' ? 'PAID' : p.status}
                        </Badge>
                      </div>
                      <div className="flex items-center gap-3 text-xs text-gray-500">
                        <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{new Date(p.created_at).toLocaleDateString()}</span>
                        {p.mpesa_receipt_number && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />M-Pesa: {p.mpesa_receipt_number}</span>}
                      </div>
                    </div>
                  </div>
                  <div className="text-right flex items-center gap-4">
                    <div>
                      <p className="text-lg font-bold text-gray-900">KES {p.amount?.toLocaleString()}</p>
                      <p className="text-xs text-gray-400">Rent Payment</p>
                    </div>
                    <Download className="w-5 h-5 text-gray-300 group-hover:text-orange-500 transition-colors" />
                  </div>
                </div>
              </Card>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Receipt Detail View ────────────────────────────────────────────────────

function ReceiptDetail({ receipt, onBack }: { receipt: any; onBack: () => void }) {
  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <button onClick={onBack} className="flex items-center gap-2 p-2 hover:bg-gray-100 rounded-xl text-gray-500">
        <ArrowLeft className="w-5 h-5" /> Back to receipts
      </button>

      {/* Digital Receipt Card */}
      <div className="bg-white rounded-3xl border-2 border-gray-100 shadow-xl overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-orange-600 to-amber-600 text-white p-8 text-center relative overflow-hidden">
          <div className="absolute top-0 right-0 w-40 h-40 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
          <div className="absolute bottom-0 left-0 w-32 h-32 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2" />
          <div className="relative z-10">
            <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center mx-auto mb-4 backdrop-blur">
              <CheckCircle className="w-8 h-8 text-white" />
            </div>
            <h2 className="text-2xl font-bold mb-1">Payment Received</h2>
            <p className="text-orange-100 text-sm">Digital Receipt — Always Available</p>
          </div>
        </div>

        {/* Receipt Body */}
        <div className="p-8 space-y-5">
          <div className="flex items-center justify-between pb-4 border-b border-gray-100">
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Receipt Number</p>
              <p className="text-lg font-bold text-gray-900 font-mono">{receipt.receipt_number}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-400 uppercase tracking-wider font-semibold">Date Paid</p>
              <p className="text-sm font-semibold text-gray-700">{receipt.paid_date}</p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">Amount Paid</p>
              <p className="text-2xl font-bold text-emerald-600">KES {receipt.amount_paid?.toLocaleString()}</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">Payment Method</p>
              <div className="flex items-center gap-2">
                <Phone className="w-5 h-5 text-emerald-600" />
                <p className="text-lg font-bold text-gray-900">M-Pesa</p>
              </div>
            </div>
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">Period</p>
              <p className="font-bold text-gray-900">{receipt.month}</p>
            </div>
            <div className="bg-gray-50 rounded-xl p-4">
              <p className="text-xs text-gray-400 mb-1">Status</p>
              <Badge variant="success" className="text-sm">PAID ✓</Badge>
            </div>
          </div>

          {receipt.mpesa_ref && (
            <div className="bg-blue-50 rounded-xl p-4">
              <p className="text-xs text-blue-500 mb-1">M-Pesa Reference</p>
              <p className="font-mono font-semibold text-blue-700">{receipt.mpesa_ref}</p>
            </div>
          )}

          {/* Vestra Guarantee */}
          <div className="flex items-center gap-3 bg-emerald-50 rounded-xl p-4 border border-emerald-100">
            <Shield className="w-6 h-6 text-emerald-600 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-emerald-800">Vestra Verified Receipt</p>
              <p className="text-xs text-emerald-600">This is an official digital receipt. Valid for tax and legal purposes. Stored permanently.</p>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-8 py-4 text-center">
          <p className="text-xs text-gray-400">Powered by Vestra — Africa's Most Trusted Property Platform</p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex gap-3">
        <Button
          className="flex-1 gap-2 bg-orange-600 hover:bg-orange-500"
          onClick={() => window.print()}
        >
          <Printer className="w-4 h-4" /> Print Receipt
        </Button>
        <Button
          variant="outline"
          className="flex-1 gap-2"
          onClick={() => {
            navigator.clipboard.writeText(receipt.receipt_number);
            alert('Receipt number copied!');
          }}
        >
          <Share2 className="w-4 h-4" /> Share Receipt
        </Button>
      </div>
    </div>
  );
}
