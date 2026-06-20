/** Market page loading skeleton — shown instantly on navigation. */
import Navbar from '@/components/layout/navbar';
import { PropertyCardSkeleton } from '@/components/property/PropertyCard';

export default function MarketLoading() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="bg-white border-b border-gray-100 sticky top-16 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex gap-2">
            <div className="flex-1 h-11 bg-gray-100 rounded-xl animate-pulse" />
            <div className="w-20 h-11 bg-gray-100 rounded-xl animate-pulse" />
            <div className="w-24 h-11 bg-gray-100 rounded-xl animate-pulse" />
          </div>
        </div>
      </div>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
          {Array.from({ length: 8 }).map((_, i) => (
            <PropertyCardSkeleton key={i} />
          ))}
        </div>
      </div>
    </div>
  );
}
