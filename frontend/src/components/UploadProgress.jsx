"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * Upload Progress Component
 *
 * Displays real-time upload progress with:
 * - File count and processing status
 * - Vector/chunk creation progress
 * - Visual progress bar
 * - Estimated completion status
 */
export default function UploadProgress({
  isVisible,
  filesUploaded = 0,
  totalFiles = 0,
  vectorsCreated = 0,
  estimatedVectors = 0,
  sessionId = null,
  onComplete = () => {},
}) {
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState("Uploading files...");

  useEffect(() => {
    console.log("📊 UploadProgress visibility changed:", isVisible);
    if (!isVisible) {
      setProgress(0);
      setStatus("Uploading files...");
      return;
    }

    // Calculate progress based on vectors created
    if (estimatedVectors > 0) {
      const calculatedProgress = Math.min(
        Math.round((vectorsCreated / estimatedVectors) * 100),
        100
      );
      setProgress(calculatedProgress);

      // Update status based on progress
      if (calculatedProgress === 0) {
        setStatus("Uploading files...");
      } else if (calculatedProgress < 30) {
        setStatus("Extracting text from documents...");
      } else if (calculatedProgress < 60) {
        setStatus("Processing tables and content...");
      } else if (calculatedProgress < 90) {
        setStatus("Creating vector embeddings...");
      } else if (calculatedProgress < 100) {
        setStatus("Finalizing...");
      } else {
        setStatus("Upload complete!");
        setTimeout(() => onComplete(), 1000);
      }
    } else if (vectorsCreated > 0) {
      // If we don't have an estimate, show indeterminate progress
      setProgress(50);
      setStatus("Processing documents...");
    }
  }, [isVisible, vectorsCreated, estimatedVectors, onComplete]);

  if (!isVisible) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 50 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -50 }}
        className="fixed bottom-8 right-8 z-50 bg-white rounded-lg shadow-2xl border border-gray-200 overflow-hidden"
        style={{ width: "400px", maxWidth: "90vw" }}
      >
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent"></div>
              <h3 className="text-white font-semibold text-lg">
                Processing Files
              </h3>
            </div>
            {sessionId && (
              <div className="text-xs text-blue-100 font-mono">
                {sessionId.slice(0, 8)}...
              </div>
            )}
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-5 space-y-4">
          {/* Status Text */}
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-gray-700">{status}</span>
            <span className="text-sm font-bold text-blue-600">{progress}%</span>
          </div>

          {/* Progress Bar */}
          <div className="relative h-3 bg-gray-200 rounded-full overflow-hidden">
            <motion.div
              className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full"
              initial={{ width: "0%" }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5, ease: "easeInOut" }}
            >
              {/* Shimmer effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white to-transparent opacity-30 animate-shimmer"></div>
            </motion.div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-2 gap-4 pt-2">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-gray-800">
                {filesUploaded}
              </div>
              <div className="text-xs text-gray-500 mt-1">Files Uploaded</div>
            </div>
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">
                {vectorsCreated}
              </div>
              <div className="text-xs text-gray-500 mt-1">Vectors Created</div>
            </div>
          </div>

          {/* Additional Info */}
          {estimatedVectors > 0 && (
            <div className="text-xs text-gray-500 text-center pt-2 border-t border-gray-100">
              Processing {vectorsCreated} of ~{estimatedVectors} text chunks
            </div>
          )}
        </div>

        {/* Footer - Optional Cancel */}
        {progress < 100 && (
          <div className="px-6 py-3 bg-gray-50 border-t border-gray-100">
            <div className="text-xs text-gray-500 text-center">
              Please wait while we process your documents...
            </div>
          </div>
        )}
      </motion.div>

      {/* Custom shimmer animation style */}
      <style jsx>{`
        @keyframes shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }
        .animate-shimmer {
          animation: shimmer 2s infinite;
        }
      `}</style>
    </AnimatePresence>
  );
}
