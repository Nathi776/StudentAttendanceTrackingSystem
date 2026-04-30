import React, { useMemo, useState } from 'react';
import { askAiChat } from '../services/api';

export default function AIChatBox() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Hi, I am your EduTrack assistant. Ask me about your next session, attendance percentage, enrolled courses, or lecturer.',
    },
  ]);

  const quickPrompts = [
    'What is my next session?',
    'What is my attendance percentage?',
    'What courses am I enrolled in?',
    'Who is my lecturer for CSC 201?',
  ];

  const canSend = useMemo(() => input.trim().length > 0 && !sending, [input, sending]);

  async function sendMessage(text) {
    const trimmed = text.trim();
    if (!trimmed || sending) {
      return;
    }

    setMessages((prev) => [...prev, { role: 'user', text: trimmed }]);
    setInput('');
    setSending(true);

    try {
      const response = await askAiChat(trimmed);
      const reply = response?.reply || 'I could not generate a response right now.';
      setMessages((prev) => [...prev, { role: 'assistant', text: reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: 'Chat is temporarily unavailable. Please try again in a moment.',
        },
      ]);
    } finally {
      setSending(false);
    }
  }

  async function onSubmit(event) {
    event.preventDefault();
    await sendMessage(input);
  }

  return (
    <div style={{ position: 'fixed', right: 20, bottom: 20, zIndex: 9999 }}>
      {!open ? (
        <button
          type="button"
          onClick={() => setOpen(true)}
          aria-label="Open AI chat"
          style={{
            borderRadius: 999,
            border: 'none',
            padding: '0.8rem 1rem',
            background: '#2563eb',
            color: '#fff',
            fontWeight: 700,
            boxShadow: '0 10px 28px rgba(37,99,235,0.35)',
          }}
        >
          AI Chat
        </button>
      ) : (
        <div
          style={{
            width: 340,
            maxWidth: 'calc(100vw - 24px)',
            borderRadius: 16,
            overflow: 'hidden',
            background: 'var(--bg)',
            border: '1px solid rgba(0,0,0,0.12)',
            boxShadow: '0 20px 42px rgba(2,6,23,0.3)',
          }}
        >
          <div
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              background: '#1d4ed8',
              color: '#fff',
              padding: '0.7rem 0.85rem',
              fontWeight: 700,
            }}
          >
            <span>EduTrack Assistant</span>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close AI chat"
              style={{
                border: 'none',
                background: 'transparent',
                color: '#fff',
                fontSize: '1.2rem',
                lineHeight: 1,
                padding: 0,
              }}
            >
              ×
            </button>
          </div>

          <div
            style={{
              height: 280,
              overflowY: 'auto',
              padding: '0.8rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.6rem',
            }}
          >
            {messages.map((msg, idx) => (
              <div
                key={`${msg.role}-${idx}`}
                style={{
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  background: msg.role === 'user' ? '#2563eb' : 'rgba(37,99,235,0.12)',
                  color: msg.role === 'user' ? '#fff' : 'var(--text)',
                  borderRadius: 12,
                  padding: '0.55rem 0.7rem',
                  maxWidth: '88%',
                  fontSize: '0.92rem',
                }}
              >
                {msg.text}
              </div>
            ))}
            {sending && (
              <div style={{ color: 'var(--text)', opacity: 0.7, fontSize: '0.9rem' }}>Thinking...</div>
            )}
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, padding: '0 0.8rem 0.8rem' }}>
            {quickPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                onClick={() => sendMessage(prompt)}
                disabled={sending}
                style={{
                  border: '1px solid rgba(37,99,235,0.28)',
                  background: 'rgba(37,99,235,0.08)',
                  color: 'var(--text)',
                  borderRadius: 999,
                  padding: '0.35rem 0.65rem',
                  fontSize: '0.82rem',
                }}
              >
                {prompt}
              </button>
            ))}
          </div>

          <form onSubmit={onSubmit} style={{ display: 'flex', gap: 8, padding: '0.75rem', borderTop: '1px solid rgba(0,0,0,0.1)' }}>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me anything..."
              style={{ flex: 1, margin: 0, color: '#000' }}
            />
            <button type="submit" disabled={!canSend}>
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
