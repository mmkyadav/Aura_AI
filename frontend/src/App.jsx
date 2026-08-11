import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Eye, 
  EyeOff, 
  ArrowUp, 
  Pencil, 
  LogOut, 
  ArrowRight,
  Globe,
  Copy,
  Check,
  ThumbsUp,
  ThumbsDown,
  RotateCcw
} from 'lucide-react';
import './App.css';

const API_BASE = 'http://localhost:8000/api/v1';

// Helper component to sanitize raw LaTeX and render beautiful Markdown
const FormattedMessage = ({ content }) => {
  if (!content) return null;

  // Clean raw LaTeX delimiters and operators for sleek readability
  let cleaned = content
    .replace(/\\\[\s*/g, '\n')
    .replace(/\s*\\\]/g, '\n')
    .replace(/\\\(\s*/g, '')
    .replace(/\s*\\\)/g, '')
    .replace(/\\times/g, '×')
    .replace(/\\div/g, '÷')
    .replace(/\\cdot/g, '·')
    .replace(/\\approx/g, '≈');

  return (
    <div className="markdown-content">
      <ReactMarkdown>{cleaned}</ReactMarkdown>
    </div>
  );
};

// ChatGPT-Style Action Bar (Copy, Feedback, Retry) for Assistant responses
const AssistantActionBar = ({ content, messageIndex, userId, threadId, onRetry, isLatest, isLoading }) => {
  const [copied, setCopied] = useState(false);
  const [rating, setRating] = useState(null); // 'thumbs_up' | 'thumbs_down' | null
  const [feedbackCategory, setFeedbackCategory] = useState('');

  const handleCopy = () => {
    if (content) {
      navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleFeedback = async (selectedRating, category = '') => {
    const newRating = rating === selectedRating && !category ? null : selectedRating;
    setRating(newRating);
    if (category) setFeedbackCategory(category);

    if (newRating && userId && threadId) {
      try {
        await fetch(`${API_BASE}/users/${userId}/threads/${threadId}/feedback`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            message_index: messageIndex,
            rating: newRating,
            feedback_text: category || feedbackCategory,
          }),
        });
      } catch (err) {
        console.warn('Feedback API note:', err);
      }
    }
  };

  return (
    <div className="action-bar-wrapper">
      <div className="action-bar font-sans">
        <button 
          className={`action-btn ${copied ? 'active-mint' : ''}`} 
          onClick={handleCopy} 
          title={copied ? "Copied!" : "Copy response"}
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
          {copied && <span className="action-label">Copied</span>}
        </button>

        <button 
          className={`action-btn ${rating === 'thumbs_up' ? 'active-mint' : ''}`} 
          onClick={() => handleFeedback('thumbs_up')} 
          title="Good response"
        >
          <ThumbsUp size={14} />
        </button>

        <button 
          className={`action-btn ${rating === 'thumbs_down' ? 'active-red' : ''}`} 
          onClick={() => handleFeedback('thumbs_down')} 
          title="Poor response"
        >
          <ThumbsDown size={14} />
        </button>

        {onRetry && (
          <button 
            className={`action-btn retry-btn ${rating === 'thumbs_down' ? 'highlight-retry' : ''}`} 
            onClick={onRetry} 
            disabled={isLoading}
            title="Regenerate response"
          >
            <RotateCcw size={14} className={isLoading ? "spin" : ""} />
            <span className="action-label">Try again</span>
          </button>
        )}
      </div>

      {rating === 'thumbs_down' && (
        <div className="dislike-feedback-pills">
          <span className="dislike-prompt">What went wrong?</span>
          {['Inaccurate info', 'Didn\'t follow prompt', 'Bad formatting'].map((cat) => (
            <button 
              key={cat} 
              className={`dislike-chip ${feedbackCategory === cat ? 'selected' : ''}`}
              onClick={() => handleFeedback('thumbs_down', cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default function App() {
  // ── Auth & Mode State ──────────────────────────────────────────────────────
  const [authMode, setAuthMode] = useState('signin'); // 'signin' or 'signup'
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [userName, setUserName] = useState('');
  const [email, setEmail] = useState('user_default@example.com');
  const [password, setPassword] = useState('••••••••');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  // ── Chat & Thread State ─────────────────────────────────────────────────────
  const userId = (email.split('@')[0] || 'user_default').replace(/[^a-zA-Z0-9_]/g, '');
  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const messagesEndRef = useRef(null);

  const suggestionPills = [
    'What is Rajinikanth\'s latest movie?',
    'What is today\'s date?',
    'Calculate total cost for 4 shirts at $24.50 and shoes at $89.99 plus 8% tax',
    'What is the weather in Hyderabad?'
  ];

  // ── Fetch User Threads on Login ──────────────────────────────────────────────
  const fetchThreads = async () => {
    try {
      const res = await fetch(`${API_BASE}/users/${userId}/threads`);
      if (res.ok) {
        const data = await res.json();
        setThreads(data || []);
      }
    } catch (err) {
      console.warn('Backend connection note:', err);
    }
  };

  useEffect(() => {
    if (isLoggedIn) {
      fetchThreads();
    }
  }, [isLoggedIn]);

  // Scroll to bottom when messages update
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // ── Auth Handlers ─────────────────────────────────────────────────────────────
  const handleAuthSubmit = (e) => {
    e.preventDefault();
    if (email.trim()) {
      setIsLoggedIn(true);
    }
  };

  const handleLogout = () => {
    setIsLoggedIn(false);
    setActiveThreadId(null);
    setMessages([]);
  };

  // ── Create New Chat Session ──────────────────────────────────────────────────
  const handleNewChat = () => {
    setActiveThreadId(null);
    setMessages([]);
    setInputText('');
  };

  // ── Select Thread & Load Saved Messages History ──────────────────────────────
  const selectThread = async (thread) => {
    setActiveThreadId(thread.thread_id);
    try {
      const res = await fetch(`${API_BASE}/users/${userId}/threads/${thread.thread_id}/messages`);
      if (res.ok) {
        const data = await res.json();
        if (data && data.length > 0) {
          setMessages(data);
          return;
        }
      }
    } catch (err) {
      console.warn('Could not fetch saved thread messages:', err);
    }
    // Fallback if no messages returned
    setMessages([
      { role: 'user', content: thread.title },
      { role: 'assistant', content: `Continuing session '${thread.title}'. How can I help you further?` }
    ]);
  };

  // ── Send Message Handler ─────────────────────────────────────────────────────
  const handleSendMessage = async (textToSend) => {
    const query = textToSend || inputText;
    if (!query.trim() || isLoading) return;

    setInputText('');
    
    // Add user message to UI immediately
    const userMsg = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    let currentThreadId = activeThreadId;

    try {
      // 1. Create thread if starting a fresh session
      if (!currentThreadId) {
        const createRes = await fetch(`${API_BASE}/users/${userId}/threads`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ title: query.slice(0, 30) }),
        });
        if (createRes.ok) {
          const newThread = await createRes.json();
          currentThreadId = newThread.thread_id;
          setActiveThreadId(currentThreadId);
          fetchThreads();
        } else {
          currentThreadId = `thread_${Date.now()}`;
          setActiveThreadId(currentThreadId);
        }
      }

      // 2. Post query to Aura backend engine
      const msgRes = await fetch(`${API_BASE}/users/${userId}/threads/${currentThreadId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: query, stream: false }),
      });

      if (msgRes.ok) {
        const data = await msgRes.json();
        setMessages((prev) => [
          ...prev,
          { 
            role: 'assistant', 
            content: data.content || 'Response generated.',
            tool_calls: data.tool_calls || []
          }
        ]);
        fetchThreads(); // Refresh thread list in sidebar
      } else {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', content: 'Good question. Let me process that for you.' }
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { 
          role: 'assistant', 
          content: 'I\'m processing your request. Start from the smallest version that already works, then let the rest grow around it.' 
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  // ── Retry / Regenerate Response Handler ──────────────────────────────────────
  const handleRetryMessage = (assistantIdx) => {
    if (isLoading) return;
    // Find previous user query
    let userQuery = '';
    for (let i = assistantIdx - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        userQuery = messages[i].content;
        break;
      }
    }

    if (userQuery) {
      // Remove assistant message and trigger re-generation
      setMessages((prev) => prev.filter((_, idx) => idx !== assistantIdx));
      handleSendMessage(userQuery);
    }
  };

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: AUTH VIEW (LOGIN & SIGN UP)
  // ─────────────────────────────────────────────────────────────────────────────
  if (!isLoggedIn) {
    return (
      <div className="login-screen font-sans">
        <div className="login-card">
          <div className="brand-tag">
            <span className="brand-dot"></span>
            <span>AURA</span>
          </div>

          <h1 className="login-title">
            {authMode === 'signin' ? 'Welcome back.' : 'Create an account.'}
          </h1>
          <p className="login-subtitle">
            {authMode === 'signin' 
              ? 'Sign in to pick up your threads where you left them.'
              : 'Start your journey with Aura today.'}
          </p>

          <form onSubmit={handleAuthSubmit} className="login-form">
            {authMode === 'signup' && (
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <div className="input-wrapper">
                  <input 
                    type="text" 
                    className="form-input" 
                    value={userName}
                    onChange={(e) => setUserName(e.target.value)}
                    placeholder="Your full name"
                    required
                  />
                </div>
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Email</label>
              <div className="input-wrapper">
                <input 
                  type="email" 
                  className="form-input" 
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <div className="input-wrapper">
                <input 
                  type={showPassword ? "text" : "password"} 
                  className="form-input" 
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                />
                <button 
                  type="button" 
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {authMode === 'signin' && (
              <div className="form-options">
                <label className="checkbox-label">
                  <input 
                    type="checkbox" 
                    className="checkbox-input"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                  />
                  <span>Remember me</span>
                </label>
                <a href="#forgot" className="forgot-link">Forgot password?</a>
              </div>
            )}

            <button type="submit" className="btn-primary">
              <span>{authMode === 'signin' ? 'Continue' : 'Create Account'}</span>
              <ArrowRight size={18} />
            </button>
          </form>

          <div className="divider">OR</div>

          <div className="social-buttons">
            <button className="btn-social" onClick={() => setIsLoggedIn(true)}>
              <Globe size={18} />
              <span>Continue with Google</span>
            </button>
            <button className="btn-social" onClick={() => setIsLoggedIn(true)}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
              </svg>
              <span>Continue with GitHub</span>
            </button>
          </div>

          <div className="login-footer">
            {authMode === 'signin' ? (
              <>
                <span>New here? </span>
                <span className="signup-link" onClick={() => setAuthMode('signup')}>Create an account</span>
              </>
            ) : (
              <>
                <span>Already have an account? </span>
                <span className="signup-link" onClick={() => setAuthMode('signin')}>Sign in</span>
              </>
            )}
          </div>
        </div>
      </div>
    );
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // RENDER: CHAT WORKSPACE VIEW
  // ─────────────────────────────────────────────────────────────────────────────
  return (
    <div className="app-container font-sans">
      {/* ── LEFT SIDEBAR ──────────────────────────────────────────────────── */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="aura-badge">A</div>
          <span className="aura-logo-text">Aura</span>
        </div>

        <button className="btn-new-chat" onClick={handleNewChat}>
          <Pencil size={16} />
          <span>New chat</span>
        </button>

        <div className="sidebar-section-title">HISTORY</div>

        <div className="history-list">
          {threads.length === 0 ? (
            <div className="no-history">No conversations yet.</div>
          ) : (
            threads.map((t) => (
              <div 
                key={t.thread_id} 
                className={`history-item ${activeThreadId === t.thread_id ? 'active' : ''}`}
                onClick={() => selectThread(t)}
              >
                {t.title}
              </div>
            ))
          )}
        </div>

        <div className="sidebar-footer">
          <div className="user-info">
            <div className="user-avatar">{userId.charAt(0).toUpperCase()}</div>
            <span className="user-email">{email}</span>
          </div>
          <button className="btn-icon-logout" title="Sign out" onClick={handleLogout}>
            <LogOut size={16} />
          </button>
        </div>
      </aside>

      {/* ── MAIN WORKSPACE ────────────────────────────────────────────────── */}
      <main className="main-workspace">
        {messages.length === 0 ? (
          /* EMPTY STATE VIEW */
          <div className="empty-state-view">
            <div className="session-ready-tag">
              <span className="brand-dot"></span>
              <span>SESSION READY</span>
            </div>

            <h1 className="hero-title">
              What are we working on<span className="hero-question-mark">?</span>
            </h1>

            <p className="hero-subtitle">
              A quiet place to think out loud. Start a conversation and it stays in your history on the left.
            </p>

            <div className="input-container">
              <input 
                type="text" 
                className="chat-input"
                placeholder="Ask anything..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
              />
              <button 
                className={`btn-send ${inputText.trim() ? 'active' : ''}`}
                onClick={() => handleSendMessage()}
                disabled={!inputText.trim() || isLoading}
              >
                <ArrowUp size={18} />
              </button>
            </div>

            <div className="suggestion-pills">
              {suggestionPills.map((pill, idx) => (
                <button 
                  key={idx} 
                  className="pill-item"
                  onClick={() => handleSendMessage(pill)}
                >
                  {pill}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* ACTIVE CONVERSATION VIEW */
          <div className="active-chat-view">
            <div className="chat-header">
              <span className="brand-dot"></span>
              <span>{threads.find(t => t.thread_id === activeThreadId)?.title || messages[0]?.content || 'New Session'}</span>
            </div>

            <div className="messages-container">
              {messages.map((m, idx) => (
                <div key={idx} className={`message-row ${m.role}`}>
                  {m.role === 'user' ? (
                    <div className="message-bubble-user">{m.content}</div>
                  ) : (
                    <>
                      <div className="assistant-header">
                        <span className="assistant-dash">—</span>
                        <span>AURA</span>
                        {m.tool_calls && m.tool_calls.length > 0 && (
                          <div className="tool-call-banner">
                            {m.tool_calls.map((tc, tcIdx) => (
                              <div key={tcIdx} className="tool-call-chip">
                                <span className="tool-chip-icon">⚡</span>
                                <span className="tool-chip-name">{tc.name}</span>
                                <span className={`tool-chip-protocol ${tc.via_mcp !== false ? 'mcp' : 'local'}`}>
                                  {tc.via_mcp !== false ? 'via FastMCP' : 'via Local'}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                      <div className="message-text-assistant">
                        <FormattedMessage content={m.content} />
                        <AssistantActionBar 
                          content={m.content}
                          messageIndex={idx}
                          userId={userId}
                          threadId={activeThreadId}
                          onRetry={() => handleRetryMessage(idx)}
                          isLatest={idx === messages.length - 1}
                          isLoading={isLoading}
                        />
                      </div>
                    </>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="message-row assistant">
                  <div className="assistant-header">
                    <span className="assistant-dash">—</span>
                    <span>AURA</span>
                  </div>
                  <div className="message-text-assistant">AI is thinking...</div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            <div className="chat-footer-input">
              <div className="input-container">
                <input 
                  type="text" 
                  className="chat-input"
                  placeholder="Reply..."
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                />
                <button 
                  className={`btn-send ${inputText.trim() ? 'active' : ''}`}
                  onClick={() => handleSendMessage()}
                  disabled={!inputText.trim() || isLoading}
                >
                  <ArrowUp size={18} />
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
