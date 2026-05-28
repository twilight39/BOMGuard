import { Link } from '@tanstack/react-router'

export function Navbar() {
  return (
    <nav className="border-b px-4 py-3 flex items-center justify-between">
      <Link to="/" className="font-heading font-bold text-lg">
        BOMGuard
      </Link>
      <div className="flex gap-4 text-sm text-muted-foreground">
        <Link to="/ask">AI Assistant</Link>
        <Link to="/admin/ml">Admin</Link>
      </div>
    </nav>
  )
}
