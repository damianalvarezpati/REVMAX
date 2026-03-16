import { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      <aside
        style={{
          width: 220,
          background: '#0f172a',
          padding: '24px 0',
          flexShrink: 0,
        }}
      >
        <div style={{ padding: '0 24px 20px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ fontSize: 20, fontWeight: 700, color: '#fff' }}>RevMax</div>
          <div style={{ fontSize: 10, color: 'rgba(255,255,255,0.65)', marginTop: 6 }}>REVENUE INTELLIGENCE</div>
        </div>
        <nav style={{ padding: '16px 0' }}>
          <Link
            to="/"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 14,
              padding: '12px 24px',
              color: '#fff',
              textDecoration: 'none',
              fontWeight: 500,
              margin: '0 12px',
              borderRadius: 10,
              background: 'rgba(255,255,255,0.12)',
            }}
          >
            Analysis
          </Link>
        </nav>
      </aside>
      <main style={{ flex: 1, marginLeft: 220, padding: 24 }}>{children}</main>
    </div>
  )
}
