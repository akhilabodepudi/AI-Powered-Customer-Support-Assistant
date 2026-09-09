import { FormEvent, useEffect, useRef, useState } from 'react'
import { Bot, Check, ChevronDown, ExternalLink, Headphones, Send, ShieldCheck, Sparkles, ThumbsDown, ThumbsUp, User } from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

type Citation = { source: string; section: string; excerpt: string; score: number }
type Message = {
  id: string
  role: 'assistant' | 'user'
  text: string
  confidence?: 'high' | 'medium' | 'low'
  citations?: Citation[]
  escalated?: boolean
}

const suggestions = [
  'How long do I have to return an item?',
  'My package says delivered, but I cannot find it.',
  'How do I reset my password?',
]

function App() {
  const [messages, setMessages] = useState<Message[]>([{
    id: 'welcome', role: 'assistant',
    text: "Hi! I'm Acme's support assistant. I answer from our verified help center and show the sources I use. How can I help?",
    confidence: 'high', citations: [],
  }])
  const [input, setInput] = useState('')
  const [conversationId, setConversationId] = useState<string>()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => endRef.current?.scrollIntoView({ behavior: 'smooth' }), [messages, loading])

  async function sendMessage(text: string) {
    const clean = text.trim()
    if (!clean || loading) return
    setError('')
    setMessages((current) => [...current, { id: crypto.randomUUID(), role: 'user', text: clean }])
    setInput('')
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: clean, conversation_id: conversationId }),
      })
      if (!response.ok) throw new Error('The support service is unavailable.')
      const body = await response.json()
      setConversationId(body.conversation_id)
      setMessages((current) => [...current, {
        id: body.message_id, role: 'assistant', text: body.answer,
        confidence: body.confidence, citations: body.citations, escalated: body.escalated,
      }])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  async function rate(messageId: string, helpful: boolean) {
    await fetch(`${API_URL}/api/feedback`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message_id: messageId, helpful }),
    })
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    void sendMessage(input)
  }

  return (
    <main className="shell">
      <header className="topbar">
        <div className="brand"><span className="brand-mark"><Sparkles size={18} /></span><span>acme</span></div>
        <div className="status"><span /> Support online</div>
      </header>

      <section className="workspace">
        <aside className="sidebar">
          <div>
            <p className="eyebrow">Customer care</p>
            <h1>Answers you can trust.</h1>
            <p className="lede">Fast, grounded support using our verified policies — with a human available whenever you need one.</p>
          </div>
          <div className="trust-card">
            <ShieldCheck size={21} />
            <div><strong>Grounded in verified sources</strong><p>Every answer is checked against our help center.</p></div>
          </div>
          <button className="human-button"><Headphones size={18} /> Talk to a person <ExternalLink size={14} /></button>
        </aside>

        <section className="chat-panel" aria-label="Customer support chat">
          <div className="chat-header">
            <div className="agent-avatar"><Bot size={22} /></div>
            <div><strong>Acme Assistant</strong><p>Typically replies instantly</p></div>
          </div>

          <div className="messages" aria-live="polite">
            {messages.map((message) => <MessageCard key={message.id} message={message} onRate={rate} />)}
            {messages.length === 1 && <div className="suggestions">
              <p>Popular questions</p>
              {suggestions.map((suggestion) => <button key={suggestion} onClick={() => void sendMessage(suggestion)}>{suggestion}<span>→</span></button>)}
            </div>}
            {loading && <div className="message-row assistant"><div className="mini-avatar"><Bot size={16} /></div><div className="bubble typing"><i /><i /><i /></div></div>}
            {error && <div className="error" role="alert">{error} Please try again.</div>}
            <div ref={endRef} />
          </div>

          <form className="composer" onSubmit={submit}>
            <label htmlFor="question" className="sr-only">Ask a support question</label>
            <textarea id="question" value={input} onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void sendMessage(input) } }}
              placeholder="Ask a question…" rows={1} maxLength={2000} />
            <button disabled={!input.trim() || loading} aria-label="Send message"><Send size={18} /></button>
          </form>
          <p className="disclaimer">AI can make mistakes. Verify important information or ask for a human.</p>
        </section>
      </section>
    </main>
  )
}

function MessageCard({ message, onRate }: { message: Message; onRate: (id: string, helpful: boolean) => Promise<void> }) {
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const [rated, setRated] = useState<boolean | null>(null)
  return <div className={`message-row ${message.role}`}>
    <div className="mini-avatar">{message.role === 'assistant' ? <Bot size={16} /> : <User size={16} />}</div>
    <div className="message-content">
      <div className="bubble">{message.text}</div>
      {message.role === 'assistant' && message.id !== 'welcome' && <div className="answer-meta">
        <span className={`confidence ${message.confidence}`}><Check size={12} /> {message.confidence} confidence</span>
        {!!message.citations?.length && <button className="sources-toggle" onClick={() => setSourcesOpen(!sourcesOpen)}>
          {message.citations.length} verified source{message.citations.length > 1 ? 's' : ''}<ChevronDown className={sourcesOpen ? 'rotate' : ''} size={14} />
        </button>}
        <span className="rating-label">Helpful?</span>
        <button className={rated === true ? 'rated' : ''} aria-label="Helpful" onClick={() => { setRated(true); void onRate(message.id, true) }}><ThumbsUp size={14} /></button>
        <button className={rated === false ? 'rated' : ''} aria-label="Not helpful" onClick={() => { setRated(false); void onRate(message.id, false) }}><ThumbsDown size={14} /></button>
      </div>}
      {sourcesOpen && <div className="sources">{message.citations?.map((citation, index) => <article key={`${citation.source}-${index}`}>
        <span>{index + 1}</span><div><strong>{citation.section}</strong><small>{citation.source}</small><p>{citation.excerpt}</p></div>
      </article>)}</div>}
      {message.escalated && <button className="escalate"><Headphones size={16} /> Connect with human support</button>}
    </div>
  </div>
}

export default App

