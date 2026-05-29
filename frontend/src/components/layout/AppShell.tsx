import { Link, useRouterState } from '@tanstack/react-router'
import { Outlet } from '@tanstack/react-router'

const navItems = [
  { to: '/', label: 'Dashboard', icon: '◈' },
  { to: '/boms', label: 'BOMs', icon: '▤' },
  { to: '/scan/new', label: 'Scan', icon: '◎' },
  { to: '/regulations', label: 'Regulations', icon: '◉' },
  { to: '/ask', label: 'AI Assistant', icon: '◆' },
  { to: '/admin/ml', label: 'Admin', icon: '◊' },
]

export function AppShell() {
  const router = useRouterState()
  const currentPath = router.location.pathname

  return (
    <div className="min-h-screen bg-background text-foreground font-sans flex">
      {/* Sidebar */}
      <aside className="w-64 border-r bg-card flex flex-col">
        <div className="h-14 flex items-center px-6 border-b">
          <Link to="/" className="font-heading font-bold text-lg tracking-tight">
            BOMGuard
          </Link>
        </div>
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const active = currentPath === item.to || currentPath.startsWith(`${item.to}/`)
            return (
              <Link
                key={item.to}
                to={item.to}
                className={[
                  'flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors',
                  active
                    ? 'bg-primary/10 text-primary font-medium'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                ].join(' ')}
              >
                <span className="text-xs w-4 text-center">{item.icon}</span>
                {item.label}
              </Link>
            )
          })}
        </nav>
        <div className="p-4 border-t text-xs text-muted-foreground">
          v0.1.0 · feat/frontend-shell
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b flex items-center justify-between px-6 bg-card">
          <h2 className="text-sm font-medium text-muted-foreground">
            {navItems.find((n) => currentPath === n.to || currentPath.startsWith(`${n.to}/`))?.label ?? 'Page'}
          </h2>
        </header>
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
