export default function Loading() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <div className="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center mx-auto mb-3 animate-pulse">
          <span className="text-white font-bold text-base">V</span>
        </div>
        <div className="h-2 w-24 bg-gray-200 rounded mx-auto animate-pulse" />
      </div>
    </div>
  );
}
