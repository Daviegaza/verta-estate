'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { ShieldCheck, Search, Building2, Star, X } from 'lucide-react';

const STEPS = [
  { icon: Search, title: 'Browse Properties', desc: 'Use AI-powered search to find verified properties across Kenya. Try typing "3-bedroom in Kilimani under 80k".', cta: 'Search Now', href: '/market' },
  { icon: ShieldCheck, title: 'Verify Any Property', desc: 'Get an AI Trust Report for any property. Know the real ownership, fraud risks, and fair market price before you pay.', cta: 'Verify Property', href: '/verify' },
  { icon: Building2, title: 'List Your Property', desc: 'Sell or rent your property to thousands of verified buyers. Get a free Trust Score to attract serious buyers.', cta: 'List Property', href: '/properties/new' },
  { icon: Star, title: 'You Are Ready!', desc: 'Your account is set up. Verified properties get 5x more views. Start exploring or list your first property.', cta: 'Go to Dashboard', href: '/dashboard' },
];

export default function OnboardingWizard({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState(0);
  const router = useRouter();
  const current = STEPS[step];

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white dark:bg-gray-900 rounded-3xl shadow-2xl max-w-lg w-full mx-4 overflow-hidden animate-scale-in">
        {/* Progress bar */}
        <div className="flex gap-1 p-4 pb-0">
          {STEPS.map((_, i) => (
            <div key={i} className={`h-1 flex-1 rounded-full transition-all duration-500 ${i <= step ? 'bg-emerald-500' : 'bg-gray-200 dark:bg-gray-700'}`} />
          ))}
        </div>
        <div className="p-8 text-center">
          <button onClick={onClose} className="absolute top-4 right-4 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800">
            <X className="w-5 h-5 text-gray-400" />
          </button>
          <div className="w-20 h-20 bg-emerald-100 dark:bg-emerald-900/30 rounded-3xl flex items-center justify-center mx-auto mb-6">
            <current.icon className="w-10 h-10 text-emerald-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-3">{current.title}</h2>
          <p className="text-gray-500 dark:text-gray-400 text-sm leading-relaxed mb-8">{current.desc}</p>
          <div className="flex gap-3 justify-center">
            {step > 0 && (
              <Button variant="outline" onClick={() => setStep(step - 1)}>Back</Button>
            )}
            <Button onClick={() => {
              if (step < STEPS.length - 1) {
                setStep(step + 1);
              } else {
                router.push(current.href);
                onClose();
              }
            }}>
              {step < STEPS.length - 1 ? 'Next' : current.cta}
            </Button>
          </div>
          {step < STEPS.length - 1 && (
            <button onClick={onClose} className="text-xs text-gray-400 mt-4 hover:text-gray-500">Skip onboarding</button>
          )}
        </div>
      </div>
    </div>
  );
}
