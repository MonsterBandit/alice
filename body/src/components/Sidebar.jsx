import { useEffect } from 'react'
import styles from './Sidebar.module.css'

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diffDays = Math.floor((now - d) / 86400000)
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return d.toLocaleDateString(undefined, { weekday: 'long' })
  return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
}

export default function Sidebar({
  open,
  onToggle,
  conversations,
  activeId,
  onSelect,
  onNew,
  onLogout,
  user,
  loading,
}) {
  // Prevent body scroll when sidebar overlay is open on mobile
  useEffect(() => {
    const isMobile = window.matchMedia('(max-width: 767px)').matches
    if (isMobile && open) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }
    return () => {
      document.body.style.overflow = ''
    }
  }, [open])

  return (
    <>
      {/* Mobile backdrop overlay */}
      {open && (
        <div
          className={styles.backdrop}
          onClick={onToggle}
          aria-hidden="true"
        />
      )}

      <aside className={`${styles.sidebar} ${open ? styles.open : styles.closed}`}>
        <div className={styles.header}>
          {open && (
            <div className={styles.brand}>
              <span className={styles.brandIcon}>✦</span>
              <span className={styles.brandName}>Alice</span>
            </div>
          )}
          {/* Desktop toggle button */}
          <button
            className={styles.toggleBtn}
            onClick={onToggle}
            title={open ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            {open ? '◀' : '▶'}
          </button>
          {/* Mobile close button — only visible on mobile when open */}
          {open && (
            <button
              className={styles.mobileCloseBtn}
              onClick={onToggle}
              title="Close sidebar"
              aria-label="Close sidebar"
            >
              ✕
            </button>
          )}
        </div>

        {open && (
          <>
            <button className={styles.newBtn} onClick={onNew}>
              <span className={styles.newIcon}>＋</span>
              <span>New conversation</span>
            </button>

            <div className={styles.convList}>
              {loading && (
                <p className={styles.hint}>Loading…</p>
              )}
              {!loading && conversations.length === 0 && (
                <p className={styles.hint}>No conversations yet</p>
              )}
              {conversations.map((conv) => (
                <button
                  key={conv.id}
                  className={`${styles.convItem} ${conv.id === activeId ? styles.active : ''}`}
                  onClick={() => {
                    onSelect(conv.id)
                    // Close sidebar on mobile after selecting
                    if (window.matchMedia('(max-width: 767px)').matches) {
                      onToggle()
                    }
                  }}
                >
                  <span className={styles.convTitle}>
                    {conv.title || 'Untitled'}
                  </span>
                  <span className={styles.convDate}>
                    {formatDate(conv.updated_at || conv.created_at)}
                  </span>
                </button>
              ))}
            </div>

            <div className={styles.footer}>
              {user && (
                <div className={styles.userInfo}>
                  <div className={styles.avatar}>
                    {(user.name || 'U')[0].toUpperCase()}
                  </div>
                  <span className={styles.userName}>{user.name || user.id}</span>
                </div>
              )}
              <button className={styles.logoutBtn} onClick={onLogout} title="Sign out">
                ⏻
              </button>
            </div>
          </>
        )}
      </aside>
    </>
  )
}
