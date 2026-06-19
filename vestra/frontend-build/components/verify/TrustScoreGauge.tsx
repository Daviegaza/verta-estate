'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';

interface TrustScoreGaugeProps {
  score: number;
  size?: number;
  strokeWidth?: number;
  showLabel?: boolean;
  className?: string;
}

/**
 * Animated SVG circular gauge for Trust Score display.
 * Animates from 0 to the target score on mount.
 */
export default function TrustScoreGauge({
  score,
  size = 120,
  strokeWidth = 8,
  showLabel = true,
  className,
}: TrustScoreGaugeProps) {
  const [animatedScore, setAnimatedScore] = useState(0);
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = radius * 2 * Math.PI;

  const getColor = (s: number) =>
    s >= 75 ? '#10b981' : s >= 50 ? '#f59e0b' : '#ef4444';

  const getLabel = (s: number) =>
    s >= 90 ? 'Excellent' : s >= 75 ? 'Good' : s >= 50 ? 'Fair' : s >= 30 ? 'Poor' : 'Risky';

  useEffect(() => {
    // Animate from 0 to target score
    let raf: number;
    const duration = 1200; // ms
    const start = performance.now();

    const animate = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(Math.round(eased * score));

      if (progress < 1) {
        raf = requestAnimationFrame(animate);
      }
    };

    raf = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(raf);
  }, [score]);

  const offset = circumference - (animatedScore / 100) * circumference;
  const color = getColor(animatedScore);

  return (
    <div
      className={cn('relative inline-flex flex-col items-center justify-center', className)}
      style={{ width: size, height: showLabel ? size + 28 : size }}
    >
      <div className="relative" style={{ width: size, height: size }}>
        {/* Background circle */}
        <svg
          width={size}
          height={size}
          className="transform -rotate-90"
          aria-label={`Trust Score: ${score} out of 100`}
          role="img"
        >
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-gray-200 dark:text-gray-700"
          />
          {/* Animated foreground */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            style={{ transition: 'stroke-dashoffset 0.3s ease-out' }}
          />
        </svg>

        {/* Center score */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className="text-2xl font-extrabold tabular-nums"
            style={{ color }}
          >
            {animatedScore}
          </span>
        </div>

        {/* Glow effect when high score */}
        {animatedScore >= 75 && (
          <div
            className="absolute inset-0 rounded-full blur-xl opacity-20"
            style={{ background: `radial-gradient(circle, ${color}, transparent)` }}
          />
        )}
      </div>

      {showLabel && (
        <span
          className="text-xs font-semibold mt-1.5 uppercase tracking-wider"
          style={{ color }}
        >
          {getLabel(animatedScore)}
        </span>
      )}
    </div>
  );
}
