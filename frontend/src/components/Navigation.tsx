import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Shield, FileText, Database } from 'lucide-react'
import { getHealth } from '../api/client'
import type { HealthResponse } from '../types'

export function Navigation() {
  const location = useLocation()
  const [health, setHealth] = useState<HealthResponse | null>(null)

  useEffect(() => {
    const init = async () => {
      try {
        const h = await getHealth()
        setHealth(h)
      } catch {
        // silent
      }
    }
    init()
  }, [])

  const isActive = (path: string) => location.pathname === path

  return (
    <header className="border-b border-zinc-800 bg-zinc-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-[1600px] mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <Shield className="w-6 h-6 text-emerald-500" />
            <span className="text-base font-semibold tracking-tight">BrandSentinel AI</span>
            <span className="hidden sm:inline-flex items-center gap-1 text-[11px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-full px-2 py-0.5 font-medium">
              Judge Sandbox
            </span>
          </div>

          <nav className="hidden md:flex items-center gap-1">
            <Link
              to="/audit"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                isActive('/audit')
                  ? 'bg-emerald-500/10 text-emerald-400 font-medium'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
              }`}
            >
              <FileText className="w-3.5 h-3.5" />
              Content Audit
            </Link>

            <Link
              to="/knowledge"
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors ${
                isActive('/knowledge')
                  ? 'bg-emerald-500/10 text-emerald-400 font-medium'
                  : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              Knowledge Hub
            </Link>
          </nav>
        </div>

        {health && (
          <div className="text-xs text-zinc-500">
            {health.guideline_count} guidelines • {health.model}
          </div>
        )}
      </div>

      {/* Mobile Navigation */}
      <nav className="md:hidden border-t border-zinc-800 bg-zinc-950">
        <div className="max-w-[1600px] mx-auto px-4 flex items-center">
          <Link
            to="/audit"
            className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm transition-colors ${
              isActive('/audit')
                ? 'text-emerald-400 border-t-2 border-emerald-500'
                : 'text-zinc-400'
            }`}
          >
            <FileText className="w-4 h-4" />
            Audit
          </Link>

          <Link
            to="/knowledge"
            className={`flex-1 flex items-center justify-center gap-2 py-3 text-sm transition-colors ${
              isActive('/knowledge')
                ? 'text-emerald-400 border-t-2 border-emerald-500'
                : 'text-zinc-400'
            }`}
          >
            <Database className="w-4 h-4" />
            Knowledge
          </Link>
        </div>
      </nav>
    </header>
  )
}
