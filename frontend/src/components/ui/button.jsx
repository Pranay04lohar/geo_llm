"use client";

import React from "react";

export default function Button({ className = "", onClick, children, ...rest }) {
  return (
    <button
      className={`px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-500 transition-colors ${className}`}
      onClick={onClick}
      {...rest}
    >
      {children}
    </button>
  );
}
