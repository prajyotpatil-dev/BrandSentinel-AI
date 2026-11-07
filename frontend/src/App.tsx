import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuditPage } from './pages/AuditPage'
import { KnowledgeHub } from './pages/KnowledgeHub'
import { Navigation } from './components/Navigation'

function App() {
  return (
    <BrowserRouter>
      <Navigation />
      <Routes>
        <Route path="/" element={<Navigate to="/audit" replace />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/knowledge" element={<KnowledgeHub />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
