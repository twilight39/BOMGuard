import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'
import { useTheme } from '@/contexts/ThemeContext'
import { deleteMe, updateMe } from '@/services/api'

interface UserSettingsModalProps {
  open: boolean
  onClose: () => void
}

export function UserSettingsModal({ open, onClose }: UserSettingsModalProps) {
  const { user, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const [name, setName] = useState(user?.name || '')
  const [saving, setSaving] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [error, setError] = useState('')

  if (!open || !user) return null

  const handleSaveName = async () => {
    setSaving(true)
    setError('')
    try {
      await updateMe({ name })
      window.location.reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async () => {
    setDeleting(true)
    setError('')
    try {
      await deleteMe()
      logout()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to delete account')
      setDeleting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* Modal */}
      <div className="relative bg-card border rounded-xl shadow-lg w-full max-w-md mx-4 p-6 space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Account Settings</h2>
          <button
            onClick={onClose}
            className="text-muted-foreground hover:text-foreground text-xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {error && (
          <div className="text-sm text-destructive bg-destructive/10 rounded-md px-3 py-2">
            {error}
          </div>
        )}

        {/* Avatar + Basic Info */}
        <div className="flex items-center gap-4">
          {user.avatar_url ? (
            <img
              src={user.avatar_url}
              alt=""
              className="h-14 w-14 rounded-full object-cover border"
            />
          ) : (
            <div className="h-14 w-14 rounded-full bg-muted border flex items-center justify-center text-lg font-semibold text-muted-foreground">
              {(user.name || user.email).charAt(0).toUpperCase()}
            </div>
          )}
          <div className="min-w-0">
            <div className="font-medium truncate">{user.name || user.email}</div>
            <div className="text-sm text-muted-foreground truncate">{user.email}</div>
          </div>
        </div>

        {/* Name Edit */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Display Name</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="flex-1 h-8 px-2.5 rounded-md border bg-background text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <Button size="sm" onClick={handleSaveName} disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </Button>
          </div>
        </div>

        {/* Theme */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Appearance</label>
          <div className="flex rounded-md border overflow-hidden">
            {(['light', 'dark', 'system'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTheme(t)}
                className={[
                  'flex-1 px-3 py-1.5 text-sm capitalize transition-colors',
                  theme === t
                    ? 'bg-primary text-primary-foreground font-medium'
                    : 'bg-background text-muted-foreground hover:bg-muted',
                ].join(' ')}
              >
                {t}
              </button>
            ))}
          </div>
        </div>

        {/* Delete Account */}
        <div className="pt-4 border-t space-y-3">
          {!showDeleteConfirm ? (
            <Button
              variant="ghost"
              size="sm"
              className="w-full text-destructive hover:text-destructive hover:bg-destructive/10"
              onClick={() => setShowDeleteConfirm(true)}
            >
              Delete Account
            </Button>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                This will permanently delete your account and all associated data. This action cannot be undone.
              </p>
              <div className="flex gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  className="flex-1"
                  onClick={() => setShowDeleteConfirm(false)}
                >
                  Cancel
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="flex-1 text-destructive hover:text-destructive hover:bg-destructive/10"
                  onClick={handleDelete}
                  disabled={deleting}
                >
                  {deleting ? 'Deleting…' : 'Confirm Delete'}
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
