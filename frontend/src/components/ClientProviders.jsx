"use client";

import React from "react";
import AlertProvider from "@/components/AlertProvider";
import { setGlobalAlert } from "@/components/alertBus";

export default function ClientProviders({ children }) {
  return (
    <AlertProvider>
      <AlertProviderBinding>{children}</AlertProviderBinding>
    </AlertProvider>
  );
}

function AlertProviderBinding({ children }) {
  const alertModule = require("@/components/AlertProvider");
  const { useAlert } = alertModule;
  const { showSuccess, showError, showInfo } = useAlert();
  React.useEffect(() => {
    setGlobalAlert((type, title, description) => {
      if (type === 'success') showSuccess(title, description);
      else if (type === 'error') showError(title, description);
      else showInfo(title, description);
    });
  }, [showSuccess, showError, showInfo]);
  return children;
}


