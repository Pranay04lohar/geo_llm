'use client'

import { useState, useMemo } from 'react'
import AnimatedEarth from '@/components/AnimatedEarth'
import CollapsibleSidebar from '@/components/CollapsibleSidebar'

export default function Home() {
  const [leftCollapsed, setLeftCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('geollm-left-sidebar-collapsed')
      return saved ? JSON.parse(saved) : true // Default to collapsed
    }
    return true
  })
  
  const [rightCollapsed, setRightCollapsed] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('geollm-right-sidebar-collapsed')
      return saved ? JSON.parse(saved) : true // Default to collapsed
    }
    return true
  })

  // Save state to localStorage whenever it changes
  const updateLeftCollapsed = (collapsed) => {
    setLeftCollapsed(collapsed)
    if (typeof window !== 'undefined') {
      localStorage.setItem('geollm-left-sidebar-collapsed', JSON.stringify(collapsed))
    }
  }

  const updateRightCollapsed = (collapsed) => {
    setRightCollapsed(collapsed)
    if (typeof window !== 'undefined') {
      localStorage.setItem('geollm-right-sidebar-collapsed', JSON.stringify(collapsed))
    }
  }

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
           onToggle={() => updateLeftCollapsed(!leftCollapsed)}
           position="left"
         >
          {/* Header with Logo */}
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center gap-4 mb-6">
                                           <button 
                onClick={() => updateLeftCollapsed(!leftCollapsed)}
                className="w-12 h-12 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-2xl flex items-center justify-center shadow-lg transition-all duration-200 cursor-pointer border border-blue-500/30 hover:shadow-xl hover:scale-105"
              >
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
                </svg>
              </button>
              <div className="flex items-center gap-3">
                <span className="text-white font-bold text-2xl">GeoLLM</span>
              </div>
            </div>
            
            {/* New Chat Button with Gradient */}
            <button className="w-full bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-2xl px-6 py-4 flex items-center gap-3 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-[1.02] font-semibold text-base">
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              New Chat
            </button>
          </div>
          
          {/* Search Bar */}
          <div className="p-6">
            <div className="relative">
              <input 
                type="text" 
                placeholder="Search chats..." 
                className="w-full bg-white/8 rounded-2xl px-5 py-3 pl-12 text-white placeholder-white/60 focus:outline-none focus:bg-white/12 focus:shadow-lg transition-all duration-200 shadow-lg border border-white/15 focus:border-white/25 text-sm"
              />
              <svg className="w-5 h-5 absolute left-4 top-3.5 text-white/60" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
          </div>
          
          {/* Chat History */}
          <div className="flex-1 overflow-y-auto px-6 space-y-3">
            <div className="text-xs text-white/60 uppercase tracking-wider mb-4 font-semibold">Recent Chats</div>
            {[
              { title: "Population data analysis", icon: "M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" },
              { title: "Boundary extraction India", icon: "M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 4m0 13V4m-6 3l6-3" },
              { title: "Geospatial clustering", icon: "M7 4V2a1 1 0 011-1h8a1 1 0 011 1v2m-9 0h10m-10 0a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V6a2 2 0 00-2-2" },
              { title: "Satellite imagery analysis", icon: "M21 12a9 9 0 01-9 9m9-9a9 9 0 00-9-9m9 9H3m9 9v-9m0-9v9" }
            ].map((chat, index) => (
              <div key={index} className="bg-white/8 rounded-2xl p-4 cursor-pointer transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-[1.02] border border-white/10 group">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-white/10 rounded-lg flex items-center justify-center transition-all duration-200">
                    <svg className="w-4 h-4 text-white/70 group-hover:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={chat.icon} />
                    </svg>
                  </div>
                  <p className="text-white/90 text-sm truncate transition-colors duration-200 flex-1">{chat.title}</p>
                </div>
              </div>
            ))}
          </div>
          
          {/* User Info */}
          <div className="p-6 border-t border-white/10">
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-full flex items-center justify-center shadow-lg border border-blue-500/30 transition-all duration-200 hover:shadow-xl hover:scale-105">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div className="flex-1">
                <p className="text-white text-base font-semibold">Mohit</p>
                <p className="text-white/60 text-sm flex items-center gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Free Plan
                </p>
              </div>
            </div>
            {/* Notification Indicator */}
            <div className="bg-gradient-to-r from-blue-500/20 to-cyan-500/20 rounded-2xl px-4 py-3 flex items-center justify-between shadow-lg border border-blue-500/30 transition-all duration-200 hover:shadow-xl hover:scale-105">
              <div className="flex items-center gap-2">
                <svg className="w-4 h-4 text-white/80" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5v-5zM4.19 4.19A2 2 0 006.32 3h11.36a2 2 0 011.13 1.19L21 14v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5l3.62-10.81z" />
                </svg>
                <span className="text-white text-sm font-medium">2 Updates</span>
              </div>
              <button className="text-white/80 text-sm transition-all duration-200 hover:scale-110 hover:text-white">
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
            <div className="bg-black/40 backdrop-blur-xl p-4 shadow-2xl border-b border-white/10">
              <div className="flex items-center justify-between relative">
                {/* Left: Get Plus Button */}
                <div className="flex-shrink-0">
                  <button className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-2xl px-4 py-2 text-sm font-medium transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105">
                    Get Plus
                  </button>
                </div>
                
                {/* Center: Title */}
                <div className="absolute left-1/2 transform -translate-x-1/2">
                  <h1 className="text-white font-bold text-3xl md:text-4xl">GeoLLM</h1>
                </div>
                
                {/* Right: Settings Button */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  <button className="text-white/70 hover:text-white transition-all duration-200 p-2 rounded-xl hover:scale-110 hover:bg-white/10">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
            
            {/* Chat Messages - Centered Welcome */}
            <div className="flex-1 overflow-y-auto flex items-center justify-center p-8">
              <div className="text-center max-w-2xl relative z-20 ml-16">
                <div className="text-white font-medium text-5xl mb-6 leading-tight">
                  What&apos;s on your mind today?
                </div>
                <div className="text-white/70 text-lg font-bold max-w-lg mx-auto leading-relaxed">
                  Ask me anything about geography, boundaries, or spatial data analysis
                </div>
              </div>
            </div>
            
            {/* Floating Chat Input - Bottom Center */}
            <div className="p-8 flex justify-center">
              <div className="w-full max-w-4xl">
                <div className="relative">
                  <textarea 
                    placeholder="Ask anything about geography, boundaries, or spatial data..."
                    className="w-full bg-black/50 rounded-3xl px-8 py-5 pr-20 text-white placeholder-white/60 focus:outline-none focus:bg-black/60 focus:shadow-xl resize-none shadow-xl transition-all duration-200 border border-white/10 focus:border-white/20 text-base"
                    rows={3}
                  />
                  <div className="absolute right-6 bottom-6 flex items-center gap-4">
                    <button className="text-white/60 transition-all duration-200 p-2 rounded-xl hover:scale-110 hover:bg-white/10">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                    </button>
                    <button className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-2xl p-3 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-110">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-6 justify-center">
                  <button className="text-white/60 text-sm flex items-center gap-2 transition-all duration-200 px-4 py-2 rounded-xl hover:scale-105 hover:bg-white/10">
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
        
        {/* Right Panel - Interactive Map Tools */}
                 <CollapsibleSidebar 
           isCollapsed={rightCollapsed} 
           onToggle={() => updateRightCollapsed(!rightCollapsed)}
           position="right"
         >
          {/* Map Header */}
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center justify-between">
              <h2 className="text-white font-bold text-xl">Interactive Map</h2>
                                           <button 
                onClick={() => updateRightCollapsed(!rightCollapsed)}
                className="w-12 h-12 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-2xl flex items-center justify-center shadow-lg transition-all duration-200 cursor-pointer border border-blue-500/30 hover:shadow-xl hover:scale-105"
              >
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 4m0 13V4m-6 3l6-3" />
                </svg>
              </button>
            </div>
          </div>
          
          {/* Map Toolbar - Stacked in Rounded Buttons */}
          <div className="p-6">
            <div className="space-y-4">
              {/* Drawing Tools */}
              <div className="space-y-3">
                <div className="text-xs text-white/60 uppercase tracking-wider font-semibold">Drawing Tools</div>
                <div className="flex gap-3">
                  <button className="flex-1 bg-white/10 text-white rounded-2xl px-4 py-3 text-sm font-medium transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105 border border-white/15">
                    Draw ROI
                  </button>
                  <button className="flex-1 bg-white/10 text-white rounded-2xl px-4 py-3 text-sm font-medium transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105 border border-white/15">
                    Select
                  </button>
                </div>
              </div>
              
              {/* Navigation Tools */}
              <div className="space-y-3">
                <div className="text-xs text-white/60 uppercase tracking-wider font-semibold">Navigation</div>
                <div className="flex gap-3">
                  <button className="flex-1 bg-white/10 text-white rounded-2xl px-4 py-3 text-sm font-medium transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105 border border-white/15">
                    Zoom In
                  </button>
                  <button className="flex-1 bg-white/10 text-white rounded-2xl px-4 py-3 text-sm font-medium transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105 border border-white/15">
                    Reset
                  </button>
                </div>
              </div>
              
              {/* Map Mode Toggle */}
              <div className="space-y-3">
                <div className="text-xs text-white/60 uppercase tracking-wider font-semibold">Map Mode</div>
                <div className="flex gap-3">
                  <button className="flex-1 bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-2xl px-4 py-3 text-sm font-medium shadow-lg hover:shadow-xl hover:scale-105 border border-blue-500/30 transition-all duration-200">
                    Satellite
                  </button>
                  <button className="flex-1 bg-white/10 text-white rounded-2xl px-4 py-3 text-sm font-medium transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105 border border-white/15">
                    Street
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          {/* Map Container */}
          <div className="flex-1 p-6">
            <div className="bg-white/8 rounded-3xl h-full flex items-center justify-center shadow-lg border border-white/15 transition-all duration-200">
              <div className="text-center">
                <svg className="w-20 h-20 text-white/40 mx-auto mb-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 4m0 13V4m-6 3l6-3" />
                </svg>
                <p className="text-white/70 text-base font-medium">Map visualization will appear here</p>
              </div>
            </div>
          </div>
          
          {/* Map Info - Styled Containers */}
          <div className="p-6 space-y-4 border-t border-white/10">
            <div className="bg-white/8 rounded-2xl p-4 shadow-lg border border-white/15 transition-all duration-200">
              <p className="text-white/90 text-sm font-medium">Selected Region: <span className="text-blue-400 font-semibold">None</span></p>
            </div>
            <div className="bg-white/8 rounded-2xl p-4 shadow-lg border border-white/15 transition-all duration-200">
              <p className="text-white/90 text-sm font-medium">Boundary Type: <span className="text-green-400 font-semibold">Administrative</span></p>
            </div>
          </div>
        </CollapsibleSidebar>
      </div>
    </div>
  )
}
