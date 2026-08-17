import React from 'react'

export default function WhatsAppTab() {
  return (
    <div className="rounded-2xl border border-dashed border-accent/40 bg-surface/60 p-16 text-center">
      <div className="text-6xl mb-6">💬</div>
      <h2 className="text-2xl font-bold tracking-tight mb-2">WhatsApp Campaigns</h2>
      <p className="text-gray-400 max-w-md mx-auto mb-8">
        Personalized follow-ups, bulk campaigns, and message templates are coming here.
        This space is reserved for the next big feature.
      </p>
      <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-green/40 bg-green/10 text-green text-sm">
        <span className="w-2 h-2 rounded-full bg-green pulse-dot" />
        Coming soon
      </div>
    </div>
  )
}