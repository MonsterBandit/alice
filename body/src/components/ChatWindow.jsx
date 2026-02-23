import { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble.jsx'
import TypingIndicator from './TypingIndicator.jsx'
import styles from './ChatWindow.module.css'

export default function ChatWindow({ messages, onSend, sidebarOpen, onToggleSidebar }) {
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, sending])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  async function handleSend() {
    const text = input.trim()
    if (!text || sending) return
    setInput('')
    setSending(true)
    try {
      await onSend(text)
    } finally {
      setSending(false)
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current
    if (!ta) return
    ta.style.height = 'auto'
    ta.style.height = Math.min(ta.scrollHeight, 180) + 'px'
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
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message Alice… (Enter to send, Shift+Enter for newline)"
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
