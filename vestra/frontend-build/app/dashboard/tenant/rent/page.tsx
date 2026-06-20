'use client';

import { useEffect, useState } from 'react';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import {
  CreditCard, Smartphone, Shield, ArrowLeft, CheckCircle,
  DollarSign
} from 'lucide-react';
import Link from 'next/link';

export default function TenantPayRentPage() {
  return (
    <AuthGuard requireAuth requireRoles={['tenant']}>
      <PayRentContent />
    </AuthGuard>
  );
}

function PayRentContent() {
  const [rental, setRental] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [paying, setPaying] = useState(false);
  const [paid, setPaid] = useState(false);

  useEffect(() => {
    api.client.get('/api/rentals/my-rental')
      .then(r => setRental(r.data))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handlePay = async () => {
    setPaying(true);
    try {
      await api.client.post('/api/rentals/rent/pay', {
        amount: rental?.monthly_rent_kes || 0,
        phone_number: '',
      });
      setPaid(true);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Payment failed');
    } finally {
      setPaying(false);
    }
  };

  if (loading) return (
    <div className="flex justify-center py-32"><Spinner size="lg" /></div>
  );

  if (paid) return (
    <div className="max-w-md mx-auto py-20 text-center animate-fade-in">
      <div className="w-20 h-20 bg-emerald-100 rounded-3xl flex items-center justify-center mx-auto mb-6">
        <CheckCircle className="w-10 h-10 text-emerald-600" />
      </div>
      <h2 className="text-2xl font-bold text-gray-900 mb-2">Payment Request Sent!</h2>
      <p className="text-gray-500 mb-2">Check your phone for the M-Pesa STK Push notification.</p>
      <p className="text-sm text-gray-400 mb-8">Enter your M-Pesa PIN to complete the payment.</p>
      <div className="flex gap-3 justify-center">
        <Link href="/dashboard/tenant">
          <Button variant="outline">Back to Dashboard</Button>
        </Link>
      </div>
    </div>
  );

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center gap-3 mb-2">
        <Link href="/dashboard/tenant" className="p-2 hover:bg-gray-100 rounded-xl">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pay Rent</h1>
          <p className="text-sm text-gray-500">Secure M-Pesa payment</p>
        </div>
      </div>

      {rental ? (
        <>
          <Card padding="md" className="bg-gradient-to-br from-orange-50 to-amber-50 border-orange-200">
            <div className="flex items-center justify-between mb-4">
              <div>
                <p className="text-sm text-gray-500">Rental</p>
                <p className="text-lg font-bold text-gray-900">{rental.unit_name}</p>
                <p className="text-xs text-gray-500">{rental.city}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-500">Amount Due</p>
                <p className="text-3xl font-bold text-orange-600">KES {rental.monthly_rent_kes?.toLocaleString()}</p>
              </div>
            </div>
          </Card>

          <Card padding="md">
            <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Smartphone className="w-5 h-5 text-orange-600" />
              M-Pesa Payment
            </h3>
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl">
                <div className="w-10 h-10 bg-emerald-100 rounded-xl flex items-center justify-center">
                  <Smartphone className="w-5 h-5 text-emerald-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">M-Pesa STK Push</p>
                  <p className="text-xs text-gray-500">You'll receive a prompt on your phone to enter your PIN</p>
                </div>
              </div>
              <div className="flex items-center gap-3 p-4 bg-gray-50 rounded-xl">
                <div className="w-10 h-10 bg-blue-100 rounded-xl flex items-center justify-center">
                  <Shield className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">Secure & Protected</p>
                  <p className="text-xs text-gray-500">Payment held in escrow for your protection</p>
                </div>
              </div>
            </div>
          </Card>

          <Button
            size="lg"
            onClick={handlePay}
            loading={paying}
            className="w-full gap-2 bg-orange-600 hover:bg-orange-500 text-lg py-6"
          >
            <CreditCard className="w-5 h-5" />
            Pay KES {rental.monthly_rent_kes?.toLocaleString()} via M-Pesa
          </Button>
        </>
      ) : (
        <Card className="text-center py-16">
          <DollarSign className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No active rental found.</p>
          <Link href="/dashboard/tenant">
            <Button variant="outline" className="mt-4">Back to Dashboard</Button>
          </Link>
        </Card>
      )}
    </div>
  );
}
