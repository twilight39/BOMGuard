import * as React from 'react'
import { Link, useRouterState } from '@tanstack/react-router'
import { Outlet } from '@tanstack/react-router'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'
import { UserSettingsModal } from '@/components/user/UserSettingsModal'

const navItems = [
  { to: '/', label: 'Dashboard', icon: '◈' },
  { to: '/boms', label: 'BOMs', icon: '▤' },
  { to: '/scan/new', label: 'Scan', icon: '◎' },
  { to: '/regulations', label: 'Regulations', icon: '◉' },
  { to: '/ask', label: 'AI Assistant', icon: '◆' },
  { to: '/admin/ml', label: 'Admin', icon: '◊' },
]

const segmentLabels: Record<string, string> = {
  boms: 'BOMs',
  regulations: 'Regulations',
  ask: 'AI Assistant',
  admin: 'Admin',
  ml: 'ML Dashboard',
  scan: 'Scan',
  new: 'New',
  upload: 'Upload',
}

function Breadcrumbs() {
  const router = useRouterState()
  const pathname = router.location.pathname
  const segments = pathname.split('/').filter(Boolean)

  if (segments.length === 0) {
    return (
      <span className="text-sm font-medium text-muted-foreground">Dashboard</span>
    )
  }

  const crumbs = segments.reduce<
    Array<{ path: string; label: string; isLast: boolean }>
  >((acc, segment, i) => {
    const prevPath = acc[i - 1]?.path ?? ''
    const path = `${prevPath}/${segment}`
    acc.push({
      path,
      label: segmentLabels[segment] ?? segment,
      isLast: i === segments.length - 1,
    })
    return acc
  }, [])

  return (
    <nav aria-label="breadcrumb" className="flex items-center gap-2 text-sm">
      <Link
        to="/"
        className="text-muted-foreground hover:text-foreground transition-colors"
      >
        Dashboard
      </Link>
      {crumbs.map((crumb) => (
        <React.Fragment key={crumb.path}>
          <span className="text-muted-foreground">/</span>
          {crumb.isLast ? (
            <span className="font-medium text-foreground">{crumb.label}</span>
          ) : (
            <Link
              to={crumb.path}
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              {crumb.label}
            </Link>
          )}
        </React.Fragment>
      ))}
    </nav>
  )
}

function UserAvatar({ name, email, avatarUrl }: { name: string | null; email: string; avatarUrl: string | null }) {
  const initial = (name || email).charAt(0).toUpperCase()
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt=""
        className="h-9 w-9 rounded-full object-cover border"
      />
    )
  }
  return (
    <div className="h-9 w-9 rounded-full bg-muted border flex items-center justify-center text-xs font-semibold text-muted-foreground">
      {initial}
    </div>
  )
}

function UserSection() {
  const { user, isLoading, login, logout } = useAuth()
  const [modalOpen, setModalOpen] = React.useState(false)

  return (
    <div className="p-4 border-t">
      {isLoading ? (
        <div className="text-xs text-muted-foreground text-center">Loading…</div>
      ) : user ? (
        <div className="space-y-3">
          <button
            onClick={() => setModalOpen(true)}
            className="w-full flex items-center justify-start gap-3 rounded-md hover:bg-muted/50 transition-colors py-1.5 px-2"
          >
            <UserAvatar
              name={user.name}
              email={user.email}
              avatarUrl={user.avatar_url}
            />
            <div className="text-left leading-tight min-w-0">
              <div className="text-sm font-medium truncate">
                {user.name || user.email}
              </div>
              <div className="text-xs text-muted-foreground truncate">
                {user.email}
              </div>
            </div>
          </button>
          <Button
            variant="ghost"
            size="sm"
            className="w-full bg-muted/50 hover:bg-muted"
            onClick={logout}
          >
            Logout
          </Button>
        </div>
      ) : (
        <Button variant="outline" size="sm" className="w-full" onClick={login}>
          Sign in with Google
        </Button>
      )}
      <UserSettingsModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  )
}

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
        <UserSection />
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 border-b flex items-center justify-between px-6 bg-card">
          <Breadcrumbs />
        </header>
        <main className="flex-1 overflow-auto">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
