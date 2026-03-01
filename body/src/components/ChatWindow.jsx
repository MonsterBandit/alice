import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble.jsx'
import TypingIndicator from './TypingIndicator.jsx'
import styles from './ChatWindow.module.css'

// Module-level draft variable — survives re-renders but not full page reloads
let draftMessage = ''

export default function ChatWindow({ messages, onSend, sidebarOpen, onToggleSidebar }) {
  const [input, setInput] = useState(draftMessage)
  const [sending, setSending] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  // Scroll to bottom when messages change or while sending
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  // Auto-focus the input whenever messages change (new message received)
  // or on mount. Skip on mobile to avoid the keyboard popping up unexpectedly.
  useEffect(() => {
    if (window.innerWidth > 768) {
      textareaRef.current?.focus()
    }
  }, [messages])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleInputChange(e) {
    const value = e.target.value
    draftMessage = value
    setInput(value)
  }

  async function handleSend() {
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    draftMessage = ''
    setSending(true)
    try {
      await onSend(text)
    } finally {
      setSending(false)
    }
  }

  // Auto-resize textarea: single line by default, grows with content
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    // Reset to auto so shrinking works correctly
    ta.style.height = 'auto'
    const newHeight = Math.min(Math.max(ta.scrollHeight, 44), 120)
    ta.style.height = newHeight + 'px'
  }, [input])

  const isEmpty = messages.length === 0

  return (
    <div className={styles.window}>
      {/* Top bar */}
      <div className={styles.topBar}>
        {!sidebarOpen && (
          <button className={styles.menuBtn} onClick={onToggleSidebar} title="Open sidebar">
            ☰
          </button>
        )}
        <span className={styles.topTitle}>Alice</span>
      </div>

      {/* Messages */}
      <div className={styles.messages}>
        {isEmpty && !sending && (
          <div className={styles.emptyState}>
            <span className={styles.emptyIcon}>✦</span>
            <p className={styles.emptyText}>How can I help you today?</p>
          </div>
        )}
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        {sending && <TypingIndicator />}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className={styles.inputArea}>
        <div className={styles.inputBox}>
          <textarea
            ref={textareaRef}
            className={styles.textarea}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Message Alice…"
            rows={1}
            disabled={sending}
          />
          <button
            className={styles.sendBtn}
            onClick={handleSend}
            disabled={!input.trim() || sending}
            title="Send"
          >
            ↑
          </button>
        </div>
        <p className={styles.hint}>Alice can make mistakes. Verify important information.</p>
      </div>
    </div>
  )
}
