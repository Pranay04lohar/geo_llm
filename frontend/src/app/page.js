'use client'

import { useState, useMemo, useEffect, useRef } from 'react'
import { uploadFiles as ragUploadFiles, getSessionStats as ragGetSessionStats, retrieveSimple as ragRetrieveSimple, retrieveDetailed as ragRetrieveDetailed, getLastSimple as ragGetLastSimple, getLastDetailed as ragGetLastDetailed } from '@/utils/api'
import AnimatedEarth from '@/components/AnimatedEarth'
import CollapsibleSidebar from '@/components/CollapsibleSidebar'
import MapView from '@/components/MapView'
import MiniMap from '@/components/MiniMap'
import FullScreenMap from '@/components/FullScreenMap'

export default function Home() {
  const [leftCollapsed, setLeftCollapsed] = useState(true) // Default to collapsed
  const [rightCollapsed, setRightCollapsed] = useState(true) // Deprecated: right panel removed
  const [isHydrated, setIsHydrated] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [prompt, setPrompt] = useState('')
  const [result, setResult] = useState('')
  const [earthSpeed, setEarthSpeed] = useState(0.002)
  const [cotLines, setCotLines] = useState([])
  const [messages, setMessages] = useState([])
  const cotTimersRef = useRef([])
  const messagesEndRef = useRef(null)
  const [showFullScreen, setShowFullScreen] = useState(false)
  const [roiData, setRoiData] = useState([])
  const [ragSessionId, setRagSessionId] = useState('')
  const [ragMessage, setRagMessage] = useState('')

  // Load from localStorage after hydration
  useEffect(() => {
    const savedLeft = localStorage.getItem('geollm-left-sidebar-collapsed')
    const savedRight = localStorage.getItem('geollm-right-sidebar-collapsed')
    const savedMessages = localStorage.getItem('geollm-chat-messages')
    
    if (savedLeft !== null) {
      setLeftCollapsed(JSON.parse(savedLeft))
    }
    if (savedRight !== null) {
      setRightCollapsed(JSON.parse(savedRight))
    }
    if (savedMessages !== null) {
      setMessages(JSON.parse(savedMessages))
    }
    
    setIsHydrated(true)
  }, [])

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
  const earthComponent = useMemo(() => <AnimatedEarth rotationSpeed={earthSpeed} />, [earthSpeed])

  // Hardcoded CoT script and final result text
  const COT_SCRIPT = [
    'Chain-of-Thought (CoT) Simulation:',
    'Initializing geospatial reasoning chain...',
    '',
    'Step 1: Parsing the uploaded GeoJSON boundary data.',
    'Step 2: Verifying CRS consistency across datasets.',
    'Step 3: Preprocessing population dataset – removing invalid features and empty geometries.',
    'Step 4: Performing spatial join to link population points with administrative boundaries.',
    'Step 5: Executing clustering algorithm (DBSCAN) to detect population centers.',
    'Step 6: Visualizing population clusters using color-coded boundaries and heatmaps.',
    '',
    'Sample Analytical Thought Process:',
    'Let us begin by understanding the key geospatial inputs provided by the user. First, the boundary file specifies the coordinates of administrative regions which we need to parse. Next, the population dataset includes spatial coordinates with associated demographic data.',
    'The next logical step is to preprocess these datasets by ensuring coordinate reference system (CRS) compatibility, removing invalid geometries, and handling missing data.',
    'Once data is preprocessed, a spatial join operation will associate population data points with their corresponding administrative regions.',
    'We will then apply clustering algorithms, such as K-Means or DBSCAN, to group spatial points based on density and proximity.',
    'Finally, after identifying spatial clusters, we will perform statistical summarization of population density, highlight outlier regions, and visualize the clusters on the map.',
    '',
    'Generating result output...'
  ]

  const FINAL_TEXT = `GeoLLM Response:\nAfter analyzing the provided geospatial dataset and applying spatial clustering techniques, we can conclude that the region around central India exhibits a high population density in urban areas while large portions of the surrounding terrain remain sparsely populated.\nThe clustering algorithm used (DBSCAN) successfully identified several major population centers such as Delhi, Mumbai, and Bengaluru as high-density clusters. The analysis also revealed natural geographical barriers like mountain ranges and rivers which act as separators between clusters.\nBased on the spatial distribution patterns, future urban expansion is likely to occur along major transportation corridors and river basins due to economic activities concentrating in these zones.`



  // Cleanup timers on unmount
  useEffect(() => {
    return () => {
      cotTimersRef.current.forEach((id) => clearTimeout(id))
      cotTimersRef.current = []
    }
  }, [])

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (typeof window !== 'undefined' && messages.length > 0) {
      localStorage.setItem('geollm-chat-messages', JSON.stringify(messages))
    }
  }, [messages])

  // Clear chat messages
  const clearChat = () => {
    setMessages([])
    setPrompt('')
    setResult('')
    setCotLines([])
    if (typeof window !== 'undefined') {
      localStorage.removeItem('geollm-chat-messages')
    }
  }









  // Don't render until hydrated to prevent hydration mismatch
  if (!isHydrated) {
    return (
      <div className="relative min-h-screen bg-black overflow-hidden">
        <div className="absolute inset-0 z-0 pointer-events-none">
          {earthComponent}
        </div>
        <div className="relative z-10 flex h-screen items-center justify-center">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-white/60">Loading...</p>
          </div>
        </div>
      </div>
    )
  }

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
           data-sidebar="left"
         >
          {/* Header with Logo */}
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center gap-4 mb-6">
                                           <button 
                id="left-sidebar-toggle"
                className="left-sidebar-toggle w-12 h-12 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-2xl flex items-center justify-center shadow-lg transition-all duration-200 cursor-pointer border border-blue-500/30 hover:shadow-xl hover:scale-105"
                onClick={() => updateLeftCollapsed(!leftCollapsed)}
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
            <button 
              id="new-chat-button"
              className="new-chat-button w-full bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-2xl px-6 py-4 flex items-center gap-3 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-[1.02] font-semibold text-base"
            >
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
                id="chat-search"
                type="text" 
                placeholder="Search chats..." 
                className="chat-search w-full bg-white/8 rounded-2xl px-5 py-3 pl-12 text-white placeholder-white/60 focus:outline-none focus:bg-white/12 focus:shadow-lg transition-all duration-200 shadow-lg border border-white/15 focus:border-white/25 text-sm"
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
                <div className="flex-shrink-0 flex items-center gap-3">
                  <button className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-2xl px-4 py-2 text-sm font-medium transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-105">
                    Get Plus
                  </button>
                </div>
                
                {/* Center: Title */}
                <div className="absolute left-1/2 transform -translate-x-1/2">
                  <h1 className="text-white font-bold text-3xl md:text-4xl">GeoLLM</h1>
                </div>
                
                {/* Right: Settings and Clear Chat Buttons */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  {messages.length > 0 && (
                    <button 
                      onClick={clearChat}
                      className="text-white/70 hover:text-white transition-all duration-200 p-2 rounded-xl hover:scale-110 hover:bg-white/10"
                      title="Clear chat history"
                    >
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  )}
                  <button 
                    id="settings-button"
                    className="settings-button text-white/70 hover:text-white transition-all duration-200 p-2 rounded-xl hover:scale-110 hover:bg-white/10"
                  >
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
            
            {/* Chat Messages - Welcome or Message History */}
            <div className="flex-1 overflow-y-auto p-8">
              {messages.length === 0 && !isProcessing ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center max-w-2xl relative z-20 ml-16 w-full">
                <div className="text-white font-medium text-5xl mb-6 leading-tight">
                  What&apos;s on your mind today?
                </div>
                <div className="text-white/70 text-lg font-bold max-w-lg mx-auto leading-relaxed">
                  Ask me anything about geography, boundaries, or spatial data analysis
                </div>
              </div>
                </div>
              ) : (
                <div className="max-w-6xl mx-auto space-y-4">
                  {messages.map((message, index) => (
                    <div
                      key={index}
                      className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in-up`}
                    >
                      <div
                        className={`max-w-[85%] rounded-2xl px-5 py-4 ${
                          message.type === 'user'
                            ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white'
                            : 'bg-white/10 text-white/90 border border-white/20'
                        }`}
                      >
                        {message.type === 'cot' ? (
                          <div className="flex flex-col gap-2">
                            <div className="flex items-center gap-2">
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-400"></div>
                              <span className="text-sm font-medium">Thinking...</span>
                            </div>
                            <div className="text-sm whitespace-pre-wrap">
                              {message.content}
                            </div>
                          </div>
                        ) : (
                          <div className="whitespace-pre-wrap">{message.content}</div>
                        )}
                      </div>
                    </div>
                  ))}
                  <div ref={messagesEndRef} />
                </div>
              )}
            </div>
            
            {/* Chat Input Area */}
            <div className="p-8">
              <div className="flex justify-center">
                <div className="w-full max-w-6xl">
                <div className="relative">
                  <textarea 
                      id="prompt-input"
                    placeholder="Ask anything about geography, boundaries, or spatial data..."
                      aria-label="Prompt input"
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      disabled={isProcessing}
                      className="prompt-input w-full bg-black/50 rounded-3xl px-8 py-5 pr-28 text-white placeholder-white/60 focus:outline-none focus:bg-black/60 focus:shadow-xl resize-none shadow-xl transition-all duration-200 border border-white/10 focus:border-white/20 text-base"
                    rows={3}
                  />
                  <div className="absolute right-6 bottom-6 flex items-center gap-4">
                    {/* Upload Button in Chat */}
                    <label 
                      id="file-upload"
                      className="file-upload text-white/80 transition-all duration-200 p-2 rounded-xl hover:scale-110 hover:bg-white/10 cursor-pointer"
                    >
                      <input
                        type="file"
                        multiple
                        accept=".geojson,.json,.shp,.zip,.tif,.tiff,.pdf,.txt,.docx,.md"
                        className="hidden"
                        onChange={async (event) => {
                          const files = Array.from(event.target.files || [])
                          if (files.length === 0) return
                          const lower = files.map(f => f.name.toLowerCase())
                          const isRag = lower.some(n => n.endsWith('.pdf') || n.endsWith('.txt') || n.endsWith('.docx') || n.endsWith('.md'))
                          try {
                            if (isRag) {
                              const selected = files.slice(0, 2)
                              const res = await ragUploadFiles(selected)
                              setRagSessionId(res.session_id)
                              setRagMessage(`Processed ${res.files_processed} files · ${res.documents_extracted} chunks`)
                              if (typeof window !== 'undefined') {
                                localStorage.setItem('rag_session_id', res.session_id)
                              }
                              try { await ragGetSessionStats(res.session_id) } catch {}
                            } else {
                              const file = files[0]
                              const name = file.name.toLowerCase()
                              if (name.endsWith('.geojson') || name.endsWith('.json')) {
                                const text = await file.text()
                                const data = JSON.parse(text)
                                const fc = data.type === 'FeatureCollection' ? data : { type: 'FeatureCollection', features: [data] }
                                setRoiData((prev) => {
                                  const base = prev.length
                                  const newItems = fc.features.map((feat, idx) => ({
                                    id: `roi-${base + idx + 1}`,
                                    name: feat.properties?.name || `ROI ${base + idx + 1}`,
                                    geojson: feat,
                                    color: '#3498db',
                                  }))
                                  return [...prev, ...newItems]
                                })
                                setShowFullScreen(true)
                              } else if (name.endsWith('.tif') || name.endsWith('.tiff')) {
                                alert('TIFF upload is not yet supported in the frontend. Consider server-side processing.')
                              } else if (name.endsWith('.shp') || name.endsWith('.zip')) {
                                alert('Shapefile upload is not yet supported in the frontend. Please convert to GeoJSON.')
                              } else {
                                alert('Unsupported file type. Please upload GeoJSON or RAG-supported files (.pdf, .txt, .docx, .md).')
                              }
                            }
                          } catch (e) {
                            alert('Upload failed. ' + (e?.message || ''))
                          } finally {
                            event.target.value = ''
                          }
                        }}
                      />
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2M7 10l5-5m0 0l5 5m-5-5v12" />
                      </svg>
                    </label>
                    <button className="text-white/60 transition-all duration-200 p-2 rounded-xl hover:scale-110 hover:bg-white/10" aria-label="Microphone">
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                      </svg>
                    </button>
                    <button
                      className="send-button bg-gradient-to-r from-blue-600 to-cyan-600 text-white rounded-2xl p-3 transition-all duration-200 shadow-lg hover:shadow-xl hover:scale-110 disabled:opacity-60"
                      aria-label="Send prompt"
                      disabled={isProcessing || !prompt.trim()}
                      onClick={async () => {
                        if (!prompt.trim()) return
                        
                        const userPrompt = prompt.trim()
                        setPrompt('')
                        
                        // Add user message immediately
                        setMessages(prev => [...prev, { type: 'user', content: userPrompt }])
                        
                        setIsProcessing(true)
                        setEarthSpeed(0.0005)
                        
                        // Add CoT message placeholder
                        const cotMessageId = Date.now()
                        setMessages(prev => [...prev, { type: 'cot', content: '', id: cotMessageId }])
                        
                        // progressively reveal CoT lines
                        let cotContent = ''
                        COT_SCRIPT.forEach((line, idx) => {
                          const id = setTimeout(() => {
                            cotContent += line + '\n'
                            setMessages(prev => prev.map(msg => 
                              msg.id === cotMessageId 
                                ? { ...msg, content: cotContent }
                                : msg
                            ))
                          }, 300 * idx)
                          cotTimersRef.current.push(id)
                        })
                        
                        // Call retrieval API
                        try {
                          let responseText = ''
                          let fullJson = null
                          if (ragSessionId) {
                            fullJson = await ragRetrieveDetailed(ragSessionId, userPrompt, 5, false)
                            responseText = (fullJson?.results?.[0]?.content) || 'No results found.'
                          } else {
                            fullJson = await ragRetrieveSimple(userPrompt)
                            responseText = (fullJson?.retrieved_chunks?.[0]?.content) || 'No results found.'
                          }
                          // Log full JSON for debugging/inspection
                          console.log('RAG retrieval result:', fullJson)
                          // Replace CoT placeholder with the best chunk content
                          setMessages(prev => prev.map(msg => 
                            msg.id === cotMessageId 
                              ? { type: 'assistant', content: responseText }
                              : msg
                          ))
                        } catch (e) {
                          console.error('RAG retrieval failed:', e)
                          setMessages(prev => prev.map(msg => 
                            msg.id === cotMessageId 
                              ? { type: 'assistant', content: 'Retrieval failed. Please try again.' }
                              : msg
                          ))
                        }
                        
                        setIsProcessing(false)
                        setEarthSpeed(0.002)
                      }}
                    >
                      <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                    </button>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-6 justify-center">
                  {ragSessionId && (
                    <div className="text-white/80 text-sm px-4 py-2 rounded-xl bg-white/10 border border-white/15">
                      RAG session: <span className="font-mono">{ragSessionId}</span>{ragMessage ? ` · ${ragMessage}` : ''}
                    </div>
                  )}
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
        </div>
        
        {/* Right Panel - Interactive Map Tools with MiniMap */}
                 <CollapsibleSidebar 
           isCollapsed={rightCollapsed} 
           onToggle={() => updateRightCollapsed(!rightCollapsed)}
           position="right"
           data-sidebar="right"
         >
          <div className="p-6 border-b border-white/10">
            <div className="flex items-center justify-between">
              <h2 className="text-white font-bold text-xl">Map</h2>
                                           <button 
                id="right-sidebar-toggle"
                className="right-sidebar-toggle w-12 h-12 bg-gradient-to-r from-blue-600 to-cyan-600 rounded-2xl flex items-center justify-center shadow-lg transition-all duration-200 cursor-pointer border border-blue-500/30 hover:shadow-xl hover:scale-105"
                onClick={() => updateRightCollapsed(!rightCollapsed)}
              >
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-1.447-.894L15 4m0 13V4m-6 3l6-3" />
                </svg>
              </button>
            </div>
          </div>
          <div className="p-6">
            <div 
              id="mini-map"
              className="mini-map bg-white/8 rounded-3xl overflow-hidden border border-white/15" 
              style={{ minHeight: '180px' }}
            >
              <MiniMap embedded onOpenFullScreen={() => setShowFullScreen(true)} />
                </div>
              </div>
        </CollapsibleSidebar>

        {showFullScreen && (
          <div id="fullscreen-map" className="fullscreen-map">
            <FullScreenMap
              roiData={roiData}
              onClose={() => setShowFullScreen(false)}
              onExport={(data) => {
                setRoiData(data)
                setShowFullScreen(false)
              }}
            />
          </div>
        )}

      </div>
    </div>
  )
}
