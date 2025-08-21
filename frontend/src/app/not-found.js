import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-white mb-4">404</h1>
        <h2 className="text-2xl text-white/70 mb-8">Page Not Found</h2>
        <p className="text-white/50 mb-8">The page you&apos;re looking for doesn&apos;t exist.</p>
        <Link 
          href="/" 
          className="bg-gradient-to-r from-blue-600 to-cyan-600 text-white px-6 py-3 rounded-2xl hover:shadow-xl hover:scale-105 transition-all duration-200"
        >
          Go Home
        </Link>
      </div>
    </div>
  )
}
