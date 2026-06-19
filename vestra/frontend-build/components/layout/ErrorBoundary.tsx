'use client';

import { Component, ReactNode, ErrorInfo } from 'react';
import { AlertTriangle, RefreshCw, WifiOff, ClipboardCopy, CheckCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  isOffline: boolean;
  errorId: string;
  timestamp: string;
  copied: boolean;
}

function generateErrorId(): string {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
  let id = 'ERR-';
  for (let i = 0; i < 8; i++) {
    id += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return id;
}

function formatTimestamp(): string {
  return new Date().toISOString();
}

function buildErrorDetails(
  error: Error | null,
  errorInfo: ErrorInfo | null,
  errorId: string,
  timestamp: string,
): string {
  const lines: string[] = [
    `Error ID: ${errorId}`,
    `Timestamp: ${timestamp}`,
    `URL: ${typeof window !== 'undefined' ? window.location.href : 'N/A'}`,
    `User Agent: ${typeof navigator !== 'undefined' ? navigator.userAgent : 'N/A'}`,
    '',
    '--- Error ---',
    `Name: ${error?.name || 'Unknown'}`,
    `Message: ${error?.message || 'No message'}`,
    '',
    '--- Stack Trace ---',
    error?.stack || '(no stack trace)',
  ];

  if (errorInfo?.componentStack) {
    lines.push('', '--- Component Stack ---', errorInfo.componentStack);
  }

  return lines.join('\n');
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      isOffline: false,
      errorId: '',
      timestamp: '',
      copied: false,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return {
      hasError: true,
      error,
      errorId: generateErrorId(),
      timestamp: formatTimestamp(),
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo });

    const errorId = this.state.errorId || generateErrorId();

    if (process.env.NODE_ENV === 'production') {
      console.error(
        JSON.stringify({
          event: 'error_boundary',
          error_id: errorId,
          message: error.message,
          stack: error.stack?.slice(0, 2000),
          component_stack: errorInfo.componentStack?.slice(0, 500),
          url: typeof window !== 'undefined' ? window.location.href : '',
          timestamp: this.state.timestamp,
        }),
      );
    }
  }

  componentDidMount() {
    window.addEventListener('offline', () => this.setState({ isOffline: true }));
    window.addEventListener('online', () => this.setState({ isOffline: false }));
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, copied: false });
  };

  handleReload = () => {
    window.location.reload();
  };

  handleCopyDetails = async () => {
    const { error, errorInfo, errorId, timestamp } = this.state;
    const details = buildErrorDetails(error, errorInfo, errorId, timestamp);

    try {
      await navigator.clipboard.writeText(details);
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 3000);
    } catch {
      // Fallback for older browsers or insecure contexts
      const textarea = document.createElement('textarea');
      textarea.value = details;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
      this.setState({ copied: true });
      setTimeout(() => this.setState({ copied: false }), 3000);
    }
  };

  render() {
    if (this.state.isOffline) {
      return (
        <>
          <div className="fixed top-0 left-0 right-0 bg-amber-500 text-white text-center py-2 px-4 text-sm font-medium z-50 flex items-center justify-center gap-2">
            <WifiOff className="w-4 h-4" />
            You&apos;re offline. Some features may be unavailable.
          </div>
          {this.props.children}
        </>
      );
    }

    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      const { error, errorId, timestamp, copied } = this.state;
      const stackLines = error?.stack?.split('\n').slice(0, 12) || [];

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-8">
          <div className="max-w-lg w-full bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
            <div className="text-center mb-6">
              <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <AlertTriangle className="w-8 h-8 text-red-600" />
              </div>
              <h2 className="text-xl font-bold text-gray-900 mb-1">Something went wrong</h2>
              <p className="text-gray-500 text-sm leading-relaxed">
                {error?.message || 'An unexpected error occurred.'}
              </p>
            </div>

            {/* Error reference block */}
            <div className="bg-gray-50 rounded-lg border border-gray-200 p-3 mb-4 text-xs font-mono text-gray-600 space-y-1">
              <div className="flex justify-between items-center">
                <span className="font-semibold text-gray-700">Error ID:</span>
                <span className="text-red-600 font-bold">{errorId}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="font-semibold text-gray-700">Timestamp:</span>
                <span>{timestamp ? new Date(timestamp).toLocaleString() : '—'}</span>
              </div>
            </div>

            {/* Stack trace (collapsible) */}
            {stackLines.length > 0 && (
              <details className="mb-4">
                <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700 select-none font-medium">
                  Technical Details (stack trace)
                </summary>
                <pre className="mt-2 bg-gray-900 text-gray-100 rounded-lg p-3 text-xs leading-relaxed overflow-x-auto max-h-48 overflow-y-auto">
                  {stackLines.map((line, i) => (
                    <div key={i} className={i === 0 ? 'text-red-300' : 'text-gray-300'}>
                      {line}
                    </div>
                  ))}
                </pre>
              </details>
            )}

            {/* Action buttons */}
            <div className="flex flex-col gap-2">
              <div className="flex gap-3 justify-center">
                <Button onClick={this.handleRetry} variant="outline" className="gap-2">
                  <RefreshCw className="w-4 h-4" /> Try Again
                </Button>
                <Button onClick={this.handleReload} className="gap-2">
                  Reload Page
                </Button>
              </div>
              <Button
                onClick={this.handleCopyDetails}
                variant="ghost"
                size="sm"
                className="gap-2 text-gray-500 hover:text-gray-700 mt-1"
              >
                {copied ? (
                  <>
                    <CheckCircle className="w-4 h-4 text-green-500" /> Copied to clipboard
                  </>
                ) : (
                  <>
                    <ClipboardCopy className="w-4 h-4" /> Copy Error Details
                  </>
                )}
              </Button>
            </div>

            {/* Support note */}
            <p className="text-xs text-gray-400 text-center mt-4">
              Please reference your <strong className="text-gray-500">Error ID</strong> when contacting support.
            </p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
