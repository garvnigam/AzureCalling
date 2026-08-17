import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './auth'
import Landing from './pages/Landing'
import Login from './pages/Login'
import AppShell from './pages/AppShell'

function Protected() {
  const { user, ready } = useAuth()
  if (!ready) return <div className="min-h-screen flex items-center justify-center text-gray-400">Loading…</div>
  return user ? <AppShell /> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/app" element={<Protected />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}