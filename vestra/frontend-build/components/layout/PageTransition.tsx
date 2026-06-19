'use client';

export default function PageTransition({ children }: { children: React.ReactNode }) {
  return (
    <div className="animate-fade-in" style={{ animationDuration: '300ms' }}>
      {children}
    </div>
  );
}
