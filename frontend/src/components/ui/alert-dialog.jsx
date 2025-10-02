"use client";

import React, { createContext, useContext } from "react";

// Minimal alert dialog primitives compatible with the imports used in AlertProvider

const DialogContext = createContext({ open: false, onOpenChange: () => {} });

export function AlertDialog({ open, onOpenChange, children }) {
  return (
    <DialogContext.Provider value={{ open, onOpenChange }}>
      {open ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="fixed inset-0 bg-black/60"
            onClick={() => onOpenChange?.(false)}
          />
          {children}
        </div>
      ) : null}
    </DialogContext.Provider>
  );
}

export function AlertDialogContent({ className = "", children }) {
  const { onOpenChange } = useContext(DialogContext);
  return (
    <div
      role="dialog"
      aria-modal="true"
      className={`relative z-50 w-full max-w-lg rounded-2xl shadow-xl ${className}`}
    >
      <button
        aria-label="Close"
        className="absolute right-4 top-4 text-white/60 hover:text-white"
        onClick={() => onOpenChange?.(false)}
      >
        ×
      </button>
      <div className="p-6">{children}</div>
    </div>
  );
}

export function AlertDialogHeader({ children }) {
  return <div className="mb-4">{children}</div>;
}

export function AlertDialogTitle({ className = "", children }) {
  return <h2 className={`text-lg font-semibold ${className}`}>{children}</h2>;
}

export function AlertDialogDescription({ className = "", children }) {
  return <p className={`mt-2 text-sm ${className}`}>{children}</p>;
}

export function AlertDialogFooter({ children }) {
  return <div className="mt-6 flex gap-3 justify-end">{children}</div>;
}

export function AlertDialogAction({ className = "", onClick, children }) {
  return (
    <button className={`px-4 py-2 rounded-lg ${className}`} onClick={onClick}>
      {children}
    </button>
  );
}

export function AlertDialogCancel({ className = "", onClick, children }) {
  return (
    <button className={`px-4 py-2 rounded-lg ${className}`} onClick={onClick}>
      {children}
    </button>
  );
}
