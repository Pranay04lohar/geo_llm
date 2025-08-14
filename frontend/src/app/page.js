'use client'

import { useState, useMemo } from 'react'
import AnimatedEarth from '@/components/AnimatedEarth'
import CollapsibleSidebar from '@/components/CollapsibleSidebar'

export default function Home() {
  const [leftCollapsed, setLeftCollapsed] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)

  // Memoize the Earth component to prevent re-renders
  const earthComponent = useMemo(() => <AnimatedEarth />, [])

  return (
    <div className="relative min-h-screen bg-black overflow-hidden">
      {/* Earth Background - Isolated from layout changes */}
      <div className="absolute inset-0 z-0 pointer-events-none">
        {earthComponent}
      </div>
      
      <div className="relative z-10 flex h-screen">
        {/* Left Sidebar - Chat History */}
        <CollapsibleSidebar 
          isCollapsed={leftCollapsed} 
          onToggle={() => setLeftCollapsed(!leftCollapsed)}
          position="left"
        >
          {/* Header */}
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center gap-4 mb-6">
              <button 
                onClick={() => setLeftCollapsed(!leftCollapsed)}
                className="w-10 h-10 bg-blue-600/40 backdrop-blur-sm rounded-xl flex items-center justify-center shadow-lg hover:bg-blue-600/60 hover:scale-105 transition-all duration-200 cursor-pointer border border-blue-500/20 hover:border-blue-400/40"
              >
                <span className="text-white font-bold text-lg">G</span>
              </button>
              <span className="text-white font-bold text-xl">GeoLLM</span>
            </div>
            <button className="w-full bg-gradient-to-r from-blue-600/20 to-purple-600/20 hover:from-blue-600/30 hover:to-purple-600/30 text-white rounded-xl px-6 py-4 flex items-center gap-3 transition-all duration-200 backdrop-blur-sm shadow-lg hover:shadow-xl border border-white/10 hover:border-white/20 hover:scale-[1.02] font-medium">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New chat
            </button>
          </div>
          
          {/* Search */}
          <div className="p-6">
            <div className="relative">
              <input 
                type="text" 
                placeholder="Search chats..." 
                className="w-full bg-white/5 rounded-xl px-5 py-3 pl-12 text-white placeholder-white/50 focus:outline-none focus:bg-white/10 focus:shadow-lg transition-all duration-200 backdrop-blur-sm shadow-lg border border-white/10 focus:border-white/20"
              />
              <svg className="w-5 h-5 absolute left-4 top-3.5 text-white/50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>
          
          {/* Chat History */}
          <div className="flex-1 overflow-y-auto px-6 space-y-3">
            <div className="text-xs text-white/50 uppercase tracking-wider mb-4 font-semibold">Recent Chats</div>
            {[
              "Population data analysis",
              "Boundary extraction India",
              "Geospatial clustering",
              "ROI mapping tools",
              "Administrative boundaries",
              "Satellite imagery analysis"
            ].map((chat, index) => (
              <div key={index} className="bg-white/3 hover:bg-white/8 rounded-xl p-4 cursor-pointer transition-all duration-200 backdrop-blur-sm shadow-lg hover:shadow-xl border border-white/5 hover:border-white/10 hover:scale-[1.02] group">
                <p className="text-white/80 text-sm truncate group-hover:text-white transition-colors duration-200">{chat}</p>
              </div>
            ))}
          </div>
          
          {/* User Info */}
          <div className="p-6 border-t border-white/10">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-gradient-to-br from-green-500/40 to-emerald-600/40 backdrop-blur-sm rounded-full flex items-center justify-center shadow-lg border border-green-500/30 hover:scale-105 transition-all duration-200">
                <span className="text-white font-bold text-lg">M</span>
              </div>
              <div className="flex-1">
                <p className="text-white text-base font-semibold">Mohit</p>
                <p className="text-white/50 text-sm">Free Plan</p>
              </div>
            </div>
            {/* Notification Indicator */}
            <div className="bg-gradient-to-r from-purple-500/20 to-blue-500/20 backdrop-blur-sm rounded-xl px-4 py-3 flex items-center justify-between shadow-lg border border-purple-500/30 hover:scale-105 transition-all duration-200">
              <span className="text-white text-sm font-medium">2 Updates</span>
              <button className="text-white/80 hover:text-white text-sm hover:scale-110 transition-all duration-200">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>
        </CollapsibleSidebar>
        
        {/* Center - Chat Interface */}
        <div className="flex-1 flex flex-col relative transition-all duration-300 ease-in-out">
          {/* Chat Content - Layered on top */}
          <div className="relative z-10 flex flex-col h-full transition-all duration-300 ease-in-out">
            {/* Chat Header */}
            <div className="bg-gradient-to-r from-white/5 to-white/3 backdrop-blur-xl p-6 shadow-2xl border-b border-white/10">
              <div className="flex items-center justify-between">
                <h1 className="text-white font-bold text-2xl">GeoLLM</h1>
                <div className="flex items-center gap-3">
                  <button className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 hover:from-blue-600/30 hover:to-purple-600/30 text-white rounded-xl px-4 py-2 text-sm font-medium transition-all duration-200 backdrop-blur-sm shadow-lg hover:shadow-xl border border-white/10 hover:border-white/20 hover:scale-105">
                    Get Plus
                  </button>
                  <button className="text-white/70 hover:text-white transition-all duration-200 hover:scale-110 p-2 rounded-lg hover:bg-white/5">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
            
            {/* Chat Messages */}
            <div className="flex-1 overflow-y-auto p-8 flex items-center justify-center">
              <div className="text-center">
                <div className="text-white/60 text-4xl font-light mb-4">
                  What's on your mind today?
                </div>
                <div className="text-white/40 text-md max-w-md">
                  Ask me anything about geography, boundaries, or spatial data analysis
                </div>
              </div>
            </div>
            
            {/* Centered Chat Input */}
            <div className="p-8 flex justify-center">
              <div className="w-full max-w-3xl">
                <div className="relative">
                  <textarea 
                    placeholder="Ask anything about geography, boundaries, or spatial data..."
                    className="w-full bg-white/5 rounded-2xl px-6 py-4 pr-16 text-white placeholder-white/50 focus:outline-none focus:bg-white/10 focus:shadow-2xl resize-none backdrop-blur-sm shadow-2xl transition-all duration-200 border border-white/10 focus:border-white/20 text-base"
                    rows={3}
                  />
                  <div className="absolute right-4 bottom-4 flex items-center gap-3">
                    <button className="text-white/50 hover:text-white transition-all duration-200 hover:scale-110 p-2 rounded-lg hover:bg-white/5">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                    </button>
                    <button className="bg-gradient-to-r from-blue-600/40 to-purple-600/40 hover:from-blue-700/50 hover:to-purple-700/50 text-white rounded-xl p-3 transition-all duration-200 backdrop-blur-sm shadow-lg hover:shadow-xl hover:scale-110 border border-blue-500/30 hover:border-blue-400/50">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-4 justify-center">
                  <button className="text-white/50 hover:text-white text-sm flex items-center gap-2 transition-all duration-200 hover:scale-105 px-4 py-2 rounded-lg hover:bg-white/5">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    Tools
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
        
        {/* Right Panel - Map */}
        <CollapsibleSidebar 
          isCollapsed={rightCollapsed} 
          onToggle={() => setRightCollapsed(!rightCollapsed)}
          position="right"
        >
          {/* Map Header */}
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center justify-between">
              <h2 className="text-white font-bold text-xl">Interactive Map</h2>
              <button 
                onClick={() => setRightCollapsed(!rightCollapsed)}
                className="w-10 h-10 bg-purple-600/40 backdrop-blur-sm rounded-xl flex items-center justify-center shadow-lg hover:bg-purple-600/60 hover:scale-105 transition-all duration-200 cursor-pointer border border-purple-500/20 hover:border-purple-400/40"
              >
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 4m0 13V4m-6 3l6-3" />
                </svg>
              </button>
            </div>
          </div>
          
          {/* Map Toolbar */}
          <div className="p-6">
            <div className="space-y-4">
              <div className="flex gap-3">
                <button className="flex-1 bg-white/5 hover:bg-white/10 text-white rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 backdrop-blur-sm shadow-lg hover:shadow-xl border border-white/10 hover:border-white/20 hover:scale-105">
                  Draw ROI
                </button>
                <button className="flex-1 bg-white/5 hover:bg-white/10 text-white rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 backdrop-blur-sm shadow-lg hover:shadow-xl border border-white/10 hover:border-white/20 hover:scale-105">
                  Select
                </button>
              </div>
              <div className="flex gap-3">
                <button className="flex-1 bg-white/5 hover:bg-white/10 text-white rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 backdrop-blur-sm shadow-lg hover:shadow-xl border border-white/10 hover:border-white/20 hover:scale-105">
                  Zoom In
                </button>
                <button className="flex-1 bg-white/5 hover:bg-white/10 text-white rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 backdrop-blur-sm shadow-lg hover:shadow-xl border border-white/10 hover:border-white/20 hover:scale-105">
                  Reset
                </button>
              </div>
              <div className="flex gap-3">
                <button className="flex-1 bg-gradient-to-r from-blue-600/40 to-blue-700/40 text-white rounded-xl px-4 py-3 text-sm font-medium backdrop-blur-sm shadow-lg border border-blue-500/30 hover:scale-105 transition-all duration-200">
                  Satellite
                </button>
                <button className="flex-1 bg-white/5 hover:bg-white/10 text-white rounded-xl px-4 py-3 text-sm font-medium transition-all duration-200 backdrop-blur-sm shadow-lg hover:shadow-xl border border-white/10 hover:border-white/20 hover:scale-105">
                  Street
                </button>
              </div>
            </div>
          </div>
          
          {/* Map Container */}
          <div className="flex-1 p-6">
            <div className="bg-gradient-to-br from-white/5 to-white/3 rounded-2xl h-full flex items-center justify-center backdrop-blur-sm shadow-lg border border-white/10 hover:shadow-xl transition-all duration-200">
              <div className="text-center">
                <svg className="w-20 h-20 text-white/30 mx-auto mb-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 4m0 13V4m-6 3l6-3" />
                </svg>
                <p className="text-white/60 text-base font-medium">Map visualization will appear here</p>
              </div>
            </div>
          </div>
          
          {/* Map Info */}
          <div className="p-6 space-y-3 border-t border-white/10">
            <div className="bg-gradient-to-r from-white/5 to-white/3 rounded-xl p-4 backdrop-blur-sm shadow-lg border border-white/10 hover:shadow-xl transition-all duration-200">
              <p className="text-white/80 text-sm font-medium">Selected Region: <span className="text-blue-400 font-semibold">None</span></p>
            </div>
            <div className="bg-gradient-to-r from-white/5 to-white/3 rounded-xl p-4 backdrop-blur-sm shadow-lg border border-white/10 hover:shadow-xl transition-all duration-200">
              <p className="text-white/80 text-sm font-medium">Boundary Type: <span className="text-green-400 font-semibold">Administrative</span></p>
            </div>
          </div>
        </CollapsibleSidebar>
      </div>
    </div>
  )
}
