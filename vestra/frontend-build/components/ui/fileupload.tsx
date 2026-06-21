'use client';

import * as React from 'react';
import { cn } from '@/lib/utils';
import { Upload, X, FileText, Image, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';

// ─── Types ──────────────────────────────────────────────────────────────────

interface FileUploadProps {
  accept?: string;
  maxSize?: number; // in bytes
  onUpload?: (files: File[]) => void;
  multiple?: boolean;
  label?: string;
  hint?: string;
  className?: string;
  disabled?: boolean;
  showPreviews?: boolean;
  maxFiles?: number;
}

interface PreviewFile {
  file: File;
  preview?: string; // data URL for images
  progress: number; // 0-100
  status: 'pending' | 'uploading' | 'done' | 'error';
  error?: string;
  id: string;
}

// ─── Helpers ────────────────────────────────────────────────────────────────

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function getFileIcon(mimeType: string) {
  if (mimeType.startsWith('image/')) return Image;
  return FileText;
}

function generateId() {
  return Math.random().toString(36).substring(2, 9);
}

// ─── FileUpload ─────────────────────────────────────────────────────────────

function FileUpload({
  accept,
  maxSize,
  onUpload,
  multiple = false,
  label,
  hint,
  className,
  disabled = false,
  showPreviews = true,
  maxFiles,
}: FileUploadProps) {
  const [isDragging, setIsDragging] = React.useState(false);
  const [files, setFiles] = React.useState<PreviewFile[]>([]);
  const [validationError, setValidationError] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLInputElement>(null);

  function validateFile(file: File): string | null {
    if (maxSize && file.size > maxSize) {
      return `File "${file.name}" exceeds maximum size of ${formatFileSize(maxSize)}`;
    }
    if (maxFiles && files.length >= maxFiles) {
      return `Maximum ${maxFiles} file(s) allowed`;
    }
    return null;
  }

  function processFiles(newFiles: FileList | File[]) {
    setValidationError(null);
    const fileArray = Array.from(newFiles);
    const valid: File[] = [];
    const errors: string[] = [];

    for (const file of fileArray) {
      const err = validateFile(file);
      if (err) {
        errors.push(err);
      } else {
        valid.push(file);
      }
    }

    if (errors.length > 0) {
      setValidationError(errors[0]); // Show first error
    }

    if (valid.length === 0) return;

    const newPreviews: PreviewFile[] = valid.map((file) => {
      const previewFile: PreviewFile = {
        file,
        progress: 0,
        status: 'pending',
        id: generateId(),
      };

      // Generate image preview
      if (file.type.startsWith('image/') && showPreviews) {
        const reader = new FileReader();
        reader.onload = (e) => {
          setFiles((prev) =>
            prev.map((pf) =>
              pf.id === previewFile.id ? { ...pf, preview: e.target?.result as string } : pf
            )
          );
        };
        reader.readAsDataURL(file);
      }

      return previewFile;
    });

    const updatedFiles = multiple ? [...files, ...newPreviews] : newPreviews;

    // Enforce maxFiles
    if (maxFiles && updatedFiles.length > maxFiles) {
      setFiles(updatedFiles.slice(0, maxFiles));
      setValidationError(`Maximum ${maxFiles} file(s) allowed. Extra files ignored.`);
    } else {
      setFiles(updatedFiles);
    }

    onUpload?.(valid);

    // Simulate upload progress for each file
    valid.forEach((_, idx) => {
      const fileId = newPreviews[idx].id;
      setFiles((prev) =>
        prev.map((pf) => (pf.id === fileId ? { ...pf, status: 'uploading' as const } : pf))
      );

      let progress = 0;
      const interval = setInterval(() => {
        progress += Math.random() * 30 + 5;
        if (progress >= 100) {
          progress = 100;
          clearInterval(interval);
          setFiles((prev) =>
            prev.map((pf) =>
              pf.id === fileId ? { ...pf, progress, status: 'done' as const } : pf
            )
          );
        } else {
          setFiles((prev) =>
            prev.map((pf) =>
              pf.id === fileId ? { ...pf, progress: Math.min(progress, 99) } : pf
            )
          );
        }
      }, 200);
    });
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (!disabled) setIsDragging(true);
  }

  function handleDragLeave(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (disabled) return;
    if (e.dataTransfer.files) {
      processFiles(e.dataTransfer.files);
    }
  }

  function handleClick() {
    if (!disabled) inputRef.current?.click();
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) {
      processFiles(e.target.files);
    }
    // Reset input so re-selecting same file triggers change
    e.target.value = '';
  }

  function removeFile(id: string) {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  }

  return (
    <div className={cn('w-full', className)}>
      {label && (
        <p className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
          {label}
        </p>
      )}

      {/* Drop Zone */}
      <div
        onClick={handleClick}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={cn(
          'relative flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed px-6 py-10',
          'transition-all duration-200 cursor-pointer',
          isDragging
            ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
            : 'border-gray-200 hover:border-emerald-400 hover:bg-gray-50 dark:border-gray-700 dark:hover:border-emerald-500 dark:hover:bg-gray-900',
          disabled && 'opacity-50 cursor-not-allowed hover:border-gray-200 hover:bg-transparent dark:hover:border-gray-700 dark:hover:bg-transparent',
          className
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          onChange={handleInputChange}
          className="hidden"
          aria-label={label || 'File upload'}
        />

        <div className={cn(
          'w-12 h-12 rounded-2xl flex items-center justify-center transition-colors',
          isDragging
            ? 'bg-emerald-100 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400'
            : 'bg-gray-100 text-gray-400 dark:bg-gray-800 dark:text-gray-500'
        )}>
          <Upload className="w-6 h-6" />
        </div>

        <div className="text-center">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {isDragging ? 'Drop files here' : 'Drag & drop files or click to browse'}
          </p>
          {accept && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              Accepted: {accept}
            </p>
          )}
          {maxSize && (
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Max size: {formatFileSize(maxSize)}
            </p>
          )}
        </div>
      </div>

      {hint && (
        <p className="mt-1.5 text-xs text-gray-400 dark:text-gray-500">{hint}</p>
      )}

      {validationError && (
        <p className="mt-2 text-xs text-red-500 flex items-center gap-1.5 bg-red-50 dark:bg-red-900/20 px-3 py-2 rounded-lg">
          <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
          {validationError}
        </p>
      )}

      {/* File Previews */}
      {showPreviews && files.length > 0 && (
        <ul className="mt-4 space-y-2">
          {files.map((file) => {
            const FileIcon = getFileIcon(file.file.type);
            return (
              <li
                key={file.id}
                className={cn(
                  'flex items-center gap-3 rounded-xl border px-4 py-3 transition-all duration-200',
                  'dark:border-gray-800',
                  file.status === 'error'
                    ? 'border-red-200 bg-red-50 dark:bg-red-900/20'
                    : file.status === 'done'
                      ? 'border-emerald-200 bg-emerald-50 dark:bg-emerald-900/20'
                      : 'border-gray-100 bg-white dark:bg-gray-900 dark:border-gray-800'
                )}
              >
                {/* Preview thumbnail */}
                {file.preview ? (
                  <img
                    src={file.preview}
                    alt={file.file.name}
                    className="w-10 h-10 rounded-lg object-cover flex-shrink-0 border border-gray-200 dark:border-gray-700"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
                    <FileIcon className="w-5 h-5 text-gray-400" />
                  </div>
                )}

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
                    {file.file.name}
                  </p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    {formatFileSize(file.file.size)}
                  </p>

                  {/* Progress bar */}
                  {file.status === 'uploading' && (
                    <div className="mt-1.5 w-full h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-emerald-500 rounded-full transition-all duration-300"
                        style={{ width: `${file.progress}%` }}
                      />
                    </div>
                  )}
                </div>

                {/* Status icon / remove */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {file.status === 'uploading' && (
                    <Loader2 className="w-4 h-4 text-emerald-500 animate-spin" />
                  )}
                  {file.status === 'done' && (
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                  )}
                  {file.status === 'error' && (
                    <AlertCircle className="w-4 h-4 text-red-500" />
                  )}
                  {(file.status === 'pending' || file.status === 'done' || file.status === 'error') && (
                    <button
                      onClick={() => removeFile(file.id)}
                      className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                      aria-label={`Remove ${file.file.name}`}
                    >
                      <X className="w-3.5 h-3.5 text-gray-400" />
                    </button>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

FileUpload.displayName = 'FileUpload';

export { FileUpload };
export type { FileUploadProps };
