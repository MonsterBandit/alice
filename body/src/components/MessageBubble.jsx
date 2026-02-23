import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { useState } from 'react'
import styles from './MessageBubble.module.css'

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // ignore
    }
  }

  return (
    <button className={styles.copyBtn} onClick={handleCopy} title="Copy code">
      {copied ? '✓ Copied' : 'Copy'}
    </button>
  )
}

function CodeBlock({ children, className }) {
  const language = className ? className.replace('language-', '') : 'text'
  const code = String(children).replace(/\n$/, '')

  return (
    <div className={styles.codeBlock}>
      <div className={styles.codeHeader}>
        <span className={styles.codeLang}>{language}</span>
        <CopyButton text={code} />
      </div>
      <SyntaxHighlighter
        style={oneDark}
        language={language}
        PreTag="div"
        customStyle={{
          margin: 0,
          borderRadius: '0 0 8px 8px',
          fontSize: '0.85rem',
          background: '#1a1d27',
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}

const markdownComponents = {
  code({ node, inline, className, children, ...props }) {
    if (inline) {
      return <code className={styles.inlineCode} {...props}>{children}</code>
    }
    return <CodeBlock className={className}>{children}</CodeBlock>
  },
}

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user'
  const isError = message.isError

  return (
    <div className={`${styles.row} ${isUser ? styles.userRow : styles.aliceRow}`}>
      {!isUser && (
        <div className={styles.aliceAvatar} title="Alice">
          ✦
        </div>
      )}
      <div
        className={`${styles.bubble} ${
          isUser ? styles.userBubble : isError ? styles.errorBubble : styles.aliceBubble
        }`}
      >
        {!isUser && (
          <span className={styles.aliceName}>Alice</span>
        )}
        <div className={styles.content}>
          {isUser ? (
            <p className={styles.userText}>{message.content}</p>
          ) : (
            <ReactMarkdown components={markdownComponents}>
              {message.content}
            </ReactMarkdown>
          )}
        </div>
      </div>
    </div>
  )
}
