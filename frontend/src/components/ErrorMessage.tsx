import React from 'react';
import { AlertCircle, XCircle } from 'lucide-react';

interface ErrorMessageProps {
  message: string;
  onDismiss?: () => void;
  onRetry?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message, onDismiss, onRetry }) => {
  if (!message) return null;

  return (
    <div className="flex items-start justify-between p-4 my-3 border rounded-lg bg-red-950/40 border-red-800/60 text-red-200">
      <div className="flex items-center space-x-3">
        <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
        <span className="text-sm font-medium">{message}</span>
      </div>
      <div className="flex items-center space-x-2 ml-4">
        {onRetry && (
          <button
            onClick={onRetry}
            className="px-2.5 py-1 text-xs font-semibold bg-red-800/60 hover:bg-red-700/80 text-white rounded transition"
          >
            Retry
          </button>
        )}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-red-400 hover:text-red-200 transition"
          >
            <XCircle className="w-5 h-5" />
          </button>
        )}
      </div>
    </div>
  );
};
