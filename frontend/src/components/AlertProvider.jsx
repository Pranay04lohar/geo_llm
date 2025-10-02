"use client";

import React, { createContext, useContext, useMemo, useState, useCallback } from "react";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

const AlertContext = createContext(null);

export const useAlert = () => {
  const ctx = useContext(AlertContext);
  if (!ctx) throw new Error("useAlert must be used within AlertProvider");
  return ctx;
};

export default function AlertProvider({ children }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [actionText, setActionText] = useState("OK");
  const [cancelText, setCancelText] = useState(null);
  const [onAction, setOnAction] = useState(null);
  const [onCancel, setOnCancel] = useState(null);
  const [variant, setVariant] = useState("default"); // default | success | error | warning | info

  const close = useCallback(() => setOpen(false), []);

  const show = useCallback(({ title, description, actionText = "OK", cancelText = null, onAction = null, onCancel = null, variant = "default" }) => {
    setTitle(title || "");
    setDescription(description || "");
    setActionText(actionText);
    setCancelText(cancelText);
    setOnAction(() => onAction);
    setOnCancel(() => onCancel);
    setVariant(variant);
    setOpen(true);
  }, []);

  const showSuccess = useCallback((title = "Success", description = "") => show({ title, description, variant: "success" }), [show]);
  const showError = useCallback((title = "Error", description = "") => show({ title, description, variant: "error" }), [show]);
  const showInfo = useCallback((title = "Info", description = "") => show({ title, description, variant: "info" }), [show]);

  const confirm = useCallback((title, description, { actionText = "Continue", cancelText = "Cancel" } = {}) => {
    return new Promise((resolve) => {
      show({ title, description, actionText, cancelText, onAction: () => resolve(true), onCancel: () => resolve(false) });
    });
  }, [show]);

  const value = useMemo(() => ({ show, showSuccess, showError, showInfo, confirm }), [show, showSuccess, showError, showInfo, confirm]);

  const titleColor = variant === "success" ? "text-emerald-400" : variant === "error" ? "text-red-400" : variant === "warning" ? "text-yellow-400" : "text-white";
  const actionClasses = variant === "success"
    ? "bg-emerald-600 hover:bg-emerald-500 text-white"
    : variant === "error"
    ? "bg-red-600 hover:bg-red-500 text-white"
    : variant === "warning"
    ? "bg-yellow-600 hover:bg-yellow-500 text-black"
    : "bg-blue-600 hover:bg-blue-500 text-white";

  return (
    <AlertContext.Provider value={value}>
      {children}
      <AlertDialog open={open} onOpenChange={setOpen}>
        <AlertDialogContent className="bg-black/90 text-white border border-white/15 backdrop-blur-xl">
          <AlertDialogHeader>
            <AlertDialogTitle className={`${titleColor}`}>{title}</AlertDialogTitle>
            {description ? (
              <AlertDialogDescription className="text-white/70">
                {description}
              </AlertDialogDescription>
            ) : null}
          </AlertDialogHeader>
          <AlertDialogFooter>
            {cancelText ? (
              <AlertDialogCancel className="bg-white/10 text-white hover:bg-white/20 border border-white/15" onClick={() => { if (onCancel) onCancel(); close(); }}>
                {cancelText}
              </AlertDialogCancel>
            ) : null}
            <AlertDialogAction className={`${actionClasses}`} onClick={() => { if (onAction) onAction(); close(); }}>
              {actionText}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AlertContext.Provider>
  );
}


