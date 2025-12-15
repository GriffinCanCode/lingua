import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'
import { initLogger, logger, LoggerProvider, LoggingErrorBoundary } from './lib/logger'

// Initialize logging system
initLogger()

const root = document.getElementById('root')!

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <LoggerProvider logger={logger}>
      <LoggingErrorBoundary
        logger={logger}
        fallback={(error, reset) => (
          <div className="min-h-screen bg-red-50 flex items-center justify-center p-8">
            <div className="max-w-md bg-white rounded-xl shadow-lg p-8">
              <h1 className="text-2xl font-bold text-red-600 mb-4">Something went wrong</h1>
              <pre className="text-sm text-red-800 bg-red-100 p-4 rounded mb-6 overflow-auto max-h-48">
                {error.message}
              </pre>
              <button
                onClick={reset}
                className="w-full bg-red-600 text-white py-3 rounded-lg hover:bg-red-700 transition font-medium"
              >
                Try Again
              </button>
            </div>
          </div>
        )}
      >
        <App />
      </LoggingErrorBoundary>
    </LoggerProvider>
  </React.StrictMode>,
)
