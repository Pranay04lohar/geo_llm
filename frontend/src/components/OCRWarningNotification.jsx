"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

/**
 * OCR Warning Notification Component
 *
 * Displays a notification alerting users that OCR functionality is unavailable.
 * Shows when files are uploaded, with auto-dismiss and manual close options.
 */
export default function OCRWarningNotification({
  isVisible,
  onClose = () => {},
  autoDismiss = true,
  dismissDelay = 8000, // 8 seconds
}) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    setShow(isVisible);

    if (isVisible && autoDismiss) {
      const timer = setTimeout(() => {
        handleClose();
      }, dismissDelay);

      return () => clearTimeout(timer);
    }
  }, [isVisible, autoDismiss, dismissDelay]);

  const handleClose = () => {
    setShow(false);
    setTimeout(() => onClose(), 300); // Wait for animation
  };

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, x: 300 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: 300 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="fixed top-8 right-8 z-50 max-w-md"
        >
          <div className="bg-white rounded-lg shadow-2xl border-l-4 border-yellow-500 overflow-hidden">
            {/* Header */}
            <div className="flex items-start p-4">
              {/* Warning Icon */}
              <div className="flex-shrink-0">
                <svg
                  className="h-6 w-6 text-yellow-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                  />
                </svg>
              </div>

              {/* Content */}
              <div className="ml-3 flex-1">
                <h3 className="text-sm font-semibold text-gray-900">
                  Limited PDF Processing
                </h3>
                <div className="mt-2 text-sm text-gray-600">
                  <p>
                    OCR and advanced table extraction are currently unavailable.
                    Some content in your PDF files may not be fully processed.
                  </p>
                  <div className="mt-3 space-y-1">
                    <p className="font-medium text-gray-700">
                      ✓ Text content will be extracted
                    </p>
                    <p className="font-medium text-yellow-700">
                      ⚠ Complex tables may be partially captured
                    </p>
                    <p className="font-medium text-yellow-700">
                      ✗ Images and graphs will be skipped
                    </p>
                  </div>
                </div>
              </div>

              {/* Close Button */}
              <div className="ml-4 flex-shrink-0">
                <button
                  onClick={handleClose}
                  className="inline-flex rounded-md text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:ring-offset-2 transition-colors"
                >
                  <span className="sr-only">Close</span>
                  <svg
                    className="h-5 w-5"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                      clipRule="evenodd"
                    />
                  </svg>
                </button>
              </div>
            </div>

            {/* Progress Bar for Auto-Dismiss */}
            {autoDismiss && (
              <div className="relative h-1 bg-gray-200">
                <motion.div
                  className="absolute top-0 left-0 h-full bg-yellow-500"
                  initial={{ width: "100%" }}
                  animate={{ width: "0%" }}
                  transition={{ duration: dismissDelay / 1000, ease: "linear" }}
                />
              </div>
            )}

            {/* Footer with Action */}
            <div className="bg-gray-50 px-4 py-3">
              <button
                onClick={handleClose}
                className="text-sm font-medium text-yellow-700 hover:text-yellow-800 transition-colors"
              >
                Dismiss
              </button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/**
 * Compact version for smaller screens or less intrusive display
 */
export function OCRWarningBanner({ isVisible, onClose = () => {} }) {
  if (!isVisible) return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -50 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -50 }}
      className="bg-yellow-50 border-l-4 border-yellow-400 p-4"
    >
      <div className="flex items-center">
        <div className="flex-shrink-0">
          <svg
            className="h-5 w-5 text-yellow-400"
            viewBox="0 0 20 20"
            fill="currentColor"
          >
            <path
              fillRule="evenodd"
              d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
              clipRule="evenodd"
            />
          </svg>
        </div>
        <div className="ml-3 flex-1">
          <p className="text-sm text-yellow-700">
            <span className="font-medium">Limited PDF processing.</span> Images
            and complex tables may not be fully processed.
          </p>
        </div>
        <div className="ml-auto pl-3">
          <div className="-mx-1.5 -my-1.5">
            <button
              onClick={onClose}
              className="inline-flex rounded-md p-1.5 text-yellow-500 hover:bg-yellow-100 focus:outline-none focus:ring-2 focus:ring-yellow-600 focus:ring-offset-2 focus:ring-offset-yellow-50"
            >
              <span className="sr-only">Dismiss</span>
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path
                  fillRule="evenodd"
                  d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                  clipRule="evenodd"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
