import { useState } from 'react'
import Layout from './components/Layout.jsx'

// View state machine for the single linear flow:
// 'form' → user fills in brand/product/brief/channels
// 'loading' → POST /generate in flight
// 'results' → per-channel compliance cards
//
// No router: the flow has no shareable URLs or browser-back requirements for POC.

export default function App() {
  const [view, setView] = useState('form')

  return (
    <Layout>
      {view === 'form' && <FormPlaceholder onSubmit={() => setView('loading')} />}
      {view === 'loading' && <LoadingPlaceholder onDone={() => setView('results')} />}
      {view === 'results' && <ResultsPlaceholder onReset={() => setView('form')} />}
    </Layout>
  )
}

function FormPlaceholder({ onSubmit }) {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Generate Compliant Copy</h1>
      <p className="text-gray-600 text-sm">
        [Placeholder] Brand selector, product name, core actives, brief textarea,
        and channel checkboxes (TikTok / Instagram / Email) go here.
      </p>
      <button
        onClick={onSubmit}
        className="px-4 py-2 bg-gray-900 text-white text-sm rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2"
      >
        Simulate Submit
      </button>
    </div>
  )
}

function LoadingPlaceholder({ onDone }) {
  return (
    <div className="space-y-4">
      <p className="text-gray-700 text-sm" role="status" aria-live="polite">
        Generating compliance-checked copy&hellip;
      </p>
      <button
        onClick={onDone}
        className="px-4 py-2 bg-gray-900 text-white text-sm rounded hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2"
      >
        Simulate Results Ready
      </button>
    </div>
  )
}

function ResultsPlaceholder({ onReset }) {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Results</h1>
      <p className="text-gray-600 text-sm">
        [Placeholder] Per-channel compliance cards go here.
        Cards render in fixed order: TikTok → Instagram → Email.
        Each card shows generation_status first (completed → badge; error → neutral/gray).
      </p>
      <button
        onClick={onReset}
        className="px-4 py-2 border border-gray-300 text-sm rounded hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-900 focus:ring-offset-2"
      >
        Start Over
      </button>
    </div>
  )
}
