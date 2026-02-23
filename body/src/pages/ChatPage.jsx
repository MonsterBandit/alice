import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../context/AuthContext.jsx'
import { setTokenGetter } from '../api/client.js'
import Sidebar from '../components/Sidebar.jsx'
import ChatWindow from '../components/ChatWindow.jsx'
import styles from './ChatPage.module.css'

export default function ChatPage() {
  const { token, user, logout } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [conversations, setConversations] = useState([])
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [messages, setMessages] = useState([])
  const [loadingConversations, setLoadingConversations] = useState(false)

  // Wire up the API client with the current token
  useEffect(() => {
    setTokenGetter(() => token)
  }, [token])

  const fetchConversations = useCallback(async () => {
    if (!token) return
    setLoadingConversations(true)
    try {
      const res = await fetch('/api/conversations', {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setConversations(data)
      }
    } catch {
      // silently fail
    } finally {
      setLoadingConversations(false)
    }
  }, [token])

  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  async function loadConversation(id) {
    setActiveConversationId(id)
    try {
      const res = await fetch(`/api/conversations/${id}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (res.ok) {
        const data = await res.json()
        setMessages(data)
      }
    } catch {
      setMessages([])
    }
  }

  function startNewConversation() {
    setActiveConversationId(null)
    setMessages([])
  }

  async function sendMessage(text) {
    const userMsg = { role: 'user', content: text, id: Date.now() }
    setMessages((prev) => [...prev, userMsg])

    try {
      const body = {
        message: text,
        user_id: user?.id || 'default',
        ...(activeConversationId ? { conversation_id: activeConversationId } : {}),
      }
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error('Chat request failed')
      const data = await res.json()

      const aliceMsg = {
        role: 'assistant',
        content: data.response || data.message || '',
        id: Date.now() + 1,
      }
      setMessages((prev) => [...prev, aliceMsg])

      // If a new conversation was created, track it
      if (data.conversation_id && !activeConversationId) {
        setActiveConversationId(data.conversation_id)
        fetchConversations()
      }
    } catch (err) {
      const errMsg = {
        role: 'assistant',
        content: `⚠️ ${err.message}`,
        id: Date.now() + 1,
        isError: true,
      }
      setMessages((prev) => [...prev, errMsg])
    }
  }

  return (
    <div className={styles.layout}>
      <Sidebar
        open={sidebarOpen}
        onToggle={() => setSidebarOpen((v) => !v)}
        conversations={conversations}
        activeId={activeConversationId}
        onSelect={loadConversation}
        onNew={startNewConversation}
        onLogout={logout}
        user={user}
        loading={loadingConversations}
      />
      <main className={styles.main}>
        <ChatWindow
          messages={messages}
          onSend={sendMessage}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((v) => !v)}
        />
      </main>
    </div>
  )
}
