'use client'

import { useState } from 'react'

export default function CollapsibleSidebar({ children, isCollapsed, onToggle, position = 'left' }) {
  return (
    <div className={`transition-all duration-300 ease-in-out ${
      position === 'left' 
        ? 'w-80' // Fixed width, use transform for collapse
        : 'w-96' // Fixed width, use transform for collapse
    }`}>
      <div className={`h-full bg-gradient-to-b from-black/30 to-black/20 backdrop-blur-xl flex flex-col relative shadow-2xl border-r border-white/10 transform transition-transform duration-300 ease-in-out ${
        isCollapsed 
          ? position === 'left' 
            ? '-translate-x-[calc(100%-3rem)]' // Show 3rem (48px) of the sidebar
            : 'translate-x-[calc(100%-3rem)]' // Show 3rem (48px) of the sidebar
          : 'translate-x-0'
      }`}>
        {/* Content */}
        <div className={`transition-opacity duration-300 ${
          isCollapsed ? 'opacity-0 pointer-events-none' : 'opacity-100'
        }`}>
          {children}
        </div>
      </div>
      
      {/* Corner positioned collapsed state - Left sidebar */}
      {isCollapsed && position === 'left' && (
        <div className="fixed left-0 top-2 h-[calc(100vh-1rem)] w-16 bg-black border-r border-white/10 z-50 flex flex-col items-center justify-start ">
          {/* Top - Clickable GeoLLM Icon */}
          <button 
            onClick={onToggle}
            className="w-12 h-12 bg-gradient-to-br from-blue-600/60 to-blue-700/60 backdrop-blur-sm rounded-xl flex items-center justify-center shadow-lg hover:from-blue-600/80 hover:to-blue-700/80 hover:scale-110 transition-all duration-200 cursor-pointer border border-blue-500/30 hover:border-blue-400/50"
          >
            <span className="text-white font-bold text-lg">G</span>
          </button>
          
          {/* Bottom - User Icon */}
          <div className="w-12 h-12 bg-gradient-to-br from-green-600/60 to-emerald-600/60 backdrop-blur-sm rounded-full flex items-center justify-center shadow-lg border border-green-500/30 hover:scale-105 transition-all duration-200">
            <span className="text-white font-bold text-lg">M</span>
          </div>
        </div>
      )}
      
      {/* Corner positioned collapsed state - Right sidebar */}
      {isCollapsed && position === 'right' && (
        <div className="fixed right-0 top-2 h-[calc(100vh-1rem)] w-16 bg-black border-l border-white/10 z-50 flex flex-col items-center justify-center">
          {/* Middle - Clickable Map Icon */}
          <button 
            onClick={onToggle}
            className="w-12 h-12 bg-gradient-to-br from-purple-600/60 to-purple-700/60 backdrop-blur-sm rounded-xl flex items-center justify-center shadow-lg hover:from-purple-600/80 hover:to-purple-700/80 hover:scale-110 transition-all duration-200 cursor-pointer border border-purple-500/30 hover:border-purple-400/50"
          >
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 4m0 13V4m-6 3l6-3" />
            </svg>
          </button>
        </div>
      )}
    </div>
  )
} 