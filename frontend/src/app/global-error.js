'use client'

export default function GlobalError({ error, reset }) {
  return (
    <html>
      <body>
        <div className="min-h-screen bg-black flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-6xl font-bold text-white mb-4">500</h1>
            <h2 className="text-2xl text-white/70 mb-8">Global Error</h2>
            <p className="text-white/50 mb-8">Something went wrong with the application.</p>
            <button 
              onClick={reset}
              className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white px-6 py-3 rounded-2xl hover:shadow-xl hover:scale-105 transition-all duration-200"
            >
              Try Again
            </button>
          </div>
        </div>
      </body>
    </html>
  )
}

