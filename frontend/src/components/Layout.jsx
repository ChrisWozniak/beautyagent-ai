export default function Layout({ children }) {
  return (
    <div className="min-h-screen flex flex-col bg-white text-gray-900">
      <header className="border-b border-gray-200 bg-white">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-baseline gap-3">
          <span className="text-xl font-semibold tracking-tight">BeautyAgent AI</span>
          <span className="text-sm text-gray-500">Compliance Copy Generator</span>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 py-8">
        {children}
      </main>

      <footer className="border-t border-gray-200 bg-gray-50">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <p className="text-xs text-gray-500">
            <strong className="font-medium text-gray-700">Compliance triage only</strong>
            {' '}— output from this tool does not constitute legal approval. Review all copy
            with your legal or regulatory team before publishing.
          </p>
        </div>
      </footer>
    </div>
  )
}
