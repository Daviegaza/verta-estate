'use client';

import { useState } from 'react';
import { Share2, Link, MessageCircle, Check } from 'lucide-react';

interface ShareButtonsProps {
  propertyId: number;
  title: string;
  className?: string;
}

export default function ShareButtons({ propertyId, title, className = '' }: ShareButtonsProps) {
  const [copied, setCopied] = useState(false);
  const url = typeof window !== 'undefined'
    ? `${window.location.origin}/properties/${propertyId}`
    : '';
  const text = `Check out this property on Vestra: ${title}`;
  const encodedText = encodeURIComponent(`${text}\n${url}`);

  const copyLink = async () => {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  const shareWhatsApp = () => {
    window.open(`https://wa.me/?text=${encodedText}`, '_blank');
  };

  const nativeShare = async () => {
    try {
      await navigator.share({ title, text, url });
    } catch {}
  };

  const canNativeShare = typeof navigator !== 'undefined' && 'share' in navigator;

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      <button
        onClick={shareWhatsApp}
        className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-xl text-sm font-medium transition-all active:scale-[0.97]"
      >
        <MessageCircle className="w-4 h-4" />
        WhatsApp
      </button>
      <button
        onClick={copyLink}
        className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl text-sm font-medium transition-all active:scale-[0.97]"
      >
        {copied ? <Check className="w-4 h-4 text-emerald-500" /> : <Link className="w-4 h-4" />}
        {copied ? 'Copied!' : 'Copy Link'}
      </button>
      {canNativeShare && (
        <button
          onClick={nativeShare}
          className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-xl text-sm font-medium transition-all active:scale-[0.97]"
        >
          <Share2 className="w-4 h-4" />
          Share
        </button>
      )}
    </div>
  );
}
