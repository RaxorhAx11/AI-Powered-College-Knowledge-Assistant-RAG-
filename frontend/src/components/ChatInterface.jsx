import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import {
  Send,
  Plus,
  Sparkles,
  ShieldCheck,
  ArrowUpRight,
  History,
  Trash2,
  ChevronLeft,
  Clock,
  Copy,
  Check,
  RotateCcw,
  MessageSquareQuote,
  Cpu,
} from 'lucide-react';
import { CitationCard } from './CitationCard';
import { Button } from './ui/Button';
import { Alert } from './ui/Alert';
import { RaxelSearchAnimation } from './RaxelSearchAnimation';
import { api } from '../services/api';
import { useToast } from '../context/ToastContext';

const EXAMPLE_PROMPTS = [
  "What is the minimum attendance requirement?",
  "When is exam registration?",
  "What are the hostel rules?",
  "What are the placement eligibility criteria?",
];

const LOCAL_STORAGE_KEY = 'raxel_chat_history_sessions';
const LOCAL_STORAGE_SETTINGS_KEY = 'raxel_llm_settings';

const DEFAULT_PROVIDER_MODELS = {
  gemini: ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash', 'gemini-2.5-flash'],
  ollama: ['llama3:latest', 'llama3', 'mistral', 'phi3'],
};

const ChatMessage = React.memo(({ msg, idx, isLast, isCopied, onCopy, onRegenerate }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}
    >
      <div
        className={`max-w-[85%] sm:max-w-[80%] p-4 text-xs sm:text-sm leading-relaxed whitespace-pre-wrap ${
          msg.role === 'user'
            ? 'rounded-2xl rounded-tr-xs bg-raxel-indigo text-white shadow-sm'
            : 'rounded-xl bg-white text-raxel-ink border border-raxel-border shadow-xs relative group overflow-hidden'
        }`}
      >
        {msg.role === 'assistant' && (
          <>
            <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-raxel-teal via-raxel-indigo to-raxel-violet" />
            <div className="flex items-center justify-between border-b border-raxel-border-subtle pb-2 mb-2">
              <div className="text-[10px] font-bold uppercase tracking-wider text-raxel-teal flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-raxel-teal animate-pulse" /> RAXEL ANSWER
                {msg.latency && (
                  <span className="text-raxel-faint font-normal lowercase">
                    ({msg.latency}s)
                  </span>
                )}
              </div>

              <div className="flex items-center gap-1">
                <button
                  onClick={() => onCopy(msg.content, idx)}
                  className="p-1 rounded text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-surface-subtle transition-colors"
                  title="Copy Answer"
                >
                  {isCopied ? (
                    <Check className="w-3.5 h-3.5 text-status-success-text" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>

                {isLast && (
                  <button
                    onClick={onRegenerate}
                    className="p-1 rounded text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-surface-subtle transition-colors"
                    title="Regenerate"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            </div>
          </>
        )}

        {msg.content}

        {msg.citations && msg.citations.length > 0 && (
          <div className="mt-3.5 pt-3 border-t border-raxel-border-subtle">
            <div className="text-[10px] font-bold uppercase tracking-wider text-raxel-muted mb-1.5">
              Official Document Sources ({msg.citations.length})
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {msg.citations.map((cit, cIdx) => (
                <CitationCard key={cIdx} citation={cit} />
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
});

export const ChatInterface = () => {
  const toast = useToast();
  const [sessions, setSessions] = useState(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);

  // LLM Provider & Model Selection State
  const [providerSettings, setProviderSettings] = useState(() => {
    try {
      const saved = localStorage.getItem(LOCAL_STORAGE_SETTINGS_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.provider && parsed.model) {
          return parsed;
        }
      }
    } catch {}
    return { provider: 'gemini', model: 'gemini-1.5-flash' };
  });

  const [availableProvidersData, setAvailableProvidersData] = useState(null);

  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const abortControllerRef = useRef(null);

  // Sync sessions state to LocalStorage
  useEffect(() => {
    try {
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(sessions));
    } catch (e) {
      console.error('Failed to save chat history:', e);
    }
  }, [sessions]);

  // Sync LLM provider settings to LocalStorage
  useEffect(() => {
    try {
      localStorage.setItem(LOCAL_STORAGE_SETTINGS_KEY, JSON.stringify(providerSettings));
    } catch (e) {
      console.error('Failed to save LLM provider settings:', e);
    }
  }, [providerSettings]);

  // Fetch available providers & models on mount
  useEffect(() => {
    api.getProviders()
      .then((data) => {
        setAvailableProvidersData(data);
        if (data && data.providers && data.providers.length > 0) {
          setProviderSettings((prev) => {
            const currentProviderInfo = data.providers.find((p) => p.id === prev.provider);
            // If current provider is configured and available, keep it
            if (currentProviderInfo && currentProviderInfo.available) {
              const models = currentProviderInfo.models || [];
              const model = models.includes(prev.model) ? prev.model : (models[0] || prev.model);
              return { ...prev, model };
            }

            // Otherwise, fallback to default_provider if available, or any available provider
            const defaultProviderInfo = data.providers.find((p) => p.id === data.default_provider && p.available);
            const activeFallback = defaultProviderInfo || data.providers.find((p) => p.available);

            if (activeFallback) {
              const models = activeFallback.models || [];
              const model = models[0] || (activeFallback.id === 'gemini' ? 'gemini-1.5-flash' : 'llama3:latest');
              return {
                provider: activeFallback.id,
                model: model,
              };
            }

            return prev;
          });
        }
      })
      .catch((err) => {
        console.warn('Could not fetch LLM providers:', err);
      });
  }, []);

  const handleProviderChange = (newProvider) => {
    const providerObj = availableProvidersData?.providers?.find((p) => p.id === newProvider);
    if (providerObj && !providerObj.available) {
      if (newProvider === 'gemini') {
        toast.info("Gemini API key is not configured in .env. To use Gemini, add GEMINI_API_KEY=AIzaSy... in .env, or use Local Ollama.");
      } else {
        toast.info(`${providerObj.name} is offline. Start it with 'ollama serve' in terminal.`);
      }
    }
    const models = providerObj?.models || DEFAULT_PROVIDER_MODELS[newProvider] || [];
    const defaultModel = models[0] || (newProvider === 'gemini' ? 'gemini-1.5-flash' : 'llama3:latest');
    setProviderSettings({ provider: newProvider, model: defaultModel });
  };

  const handleModelChange = (newModel) => {
    setProviderSettings((prev) => ({ ...prev, model: newModel }));
  };

  // Clean up in-flight requests on unmount
  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  // Load selected session messages
  useEffect(() => {
    if (currentSessionId) {
      const found = sessions.find((s) => s.id === currentSessionId);
      if (found) {
        setMessages(found.messages || []);
      }
    }
  }, [currentSessionId]);

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading]);

  const saveCurrentSession = (updatedMessages, firstQuestionText) => {
    let sId = currentSessionId;

    if (!sId) {
      sId = 'session_' + Date.now();
      setCurrentSessionId(sId);

      const title =
        firstQuestionText.length > 32
          ? firstQuestionText.substring(0, 32) + '...'
          : firstQuestionText;

      const newSession = {
        id: sId,
        title: title || 'New Conversation',
        timestamp: new Date().toLocaleTimeString([], {
          hour: '2-digit',
          minute: '2-digit',
        }),
        messages: updatedMessages,
      };

      setSessions((prev) => [newSession, ...prev]);
    } else {
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === sId) {
            return { ...s, messages: updatedMessages };
          }
          return s;
        })
      );
    }
  };

  const handleSend = async (textToSend) => {
    const question = textToSend || input;
    if (!question || !question.trim()) return;

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    setError('');
    const userMsg = { role: 'user', content: question.trim() };
    const updatedHistory = [...messages, userMsg];

    setMessages(updatedHistory);
    if (!textToSend) setInput('');
    setLoading(true);

    try {
      const historyForApi = updatedHistory
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .map((m) => ({ role: m.role, content: m.content }));

      const res = await api.sendMessage(
        question.trim(),
        null,
        historyForApi,
        undefined,
        providerSettings.provider,
        providerSettings.model,
        { signal: controller.signal }
      );

      const botMsg = {
        role: 'assistant',
        content: res.answer,
        citations: res.citations || [],
        hasSufficientEvidence: res.has_sufficient_evidence,
        isFallback: res.is_fallback,
        isAmbiguous: res.is_ambiguous,
        latency: res.latency_sec,
      };

      const fullHistory = [...updatedHistory, botMsg];
      setMessages(fullHistory);
      saveCurrentSession(fullHistory, question.trim());
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(
          err.message ||
          'RAXEL could not complete that request. Please try again.'
        );
      }
    } finally {
      if (abortControllerRef.current === controller) {
        setLoading(false);
      }
    }
  };

  const handleCopyText = (content, index) => {
    navigator.clipboard.writeText(content);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleRegenerate = () => {
    if (messages.length === 0) return;
    const lastUserMsg = [...messages].reverse().find((m) => m.role === 'user');
    if (lastUserMsg) {
      handleSend(lastUserMsg.content);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleNewChat = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    setCurrentSessionId(null);
    setMessages([]);
    setInput('');
    setError('');
  };

  const handleDeleteSession = (sessionId, e) => {
    e.stopPropagation();
    setSessions((prev) => prev.filter((s) => s.id !== sessionId));
    if (currentSessionId === sessionId) {
      handleNewChat();
    }
  };

  return (
    <div className="flex flex-1 h-[calc(100vh-64px)] min-h-0 w-full relative overflow-hidden bg-raxel-soft-white">
      {/* AMBIENT AI GLOW BACKGROUND */}
      <motion.div
        animate={{
          scale: [1, 1.06, 1],
          opacity: [0.35, 0.55, 0.35],
        }}
        transition={{ duration: 7, repeat: Infinity, ease: 'easeInOut' }}
        className="absolute top-12 left-1/2 -translate-x-1/2 w-[550px] sm:w-[650px] h-[300px] bg-gradient-to-tr from-raxel-indigo/15 via-raxel-violet/20 to-raxel-teal/15 blur-[90px] rounded-full pointer-events-none z-0"
      />

      {/* CHAT HISTORY COLLAPSIBLE SIDEBAR */}
      <AnimatePresence initial={false}>
        {historyOpen && (
          <motion.div
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 270, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="bg-white border-r border-raxel-border z-30 shrink-0 flex flex-col h-full overflow-hidden shadow-lg relative"
          >
            <div className="p-3.5 border-b border-raxel-border-subtle flex items-center justify-between bg-raxel-soft-white">
              <div className="flex items-center gap-2 font-semibold text-xs text-raxel-indigo">
                <History className="w-4 h-4 text-raxel-teal" />
                <span>Chat History</span>
              </div>
              <button
                onClick={() => setHistoryOpen(false)}
                className="p-1 rounded text-raxel-muted hover:text-raxel-indigo hover:bg-raxel-surface-subtle transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-raxel-indigo"
                aria-label="Close history"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
            </div>

            <div className="p-3">
              <Button
                variant="primary"
                size="sm"
                icon={Plus}
                onClick={handleNewChat}
                className="w-full justify-center"
              >
                New Chat
              </Button>
            </div>

            {/* Sessions List */}
            <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
              {sessions.length === 0 ? (
                <div className="text-xs text-raxel-faint text-center py-10 px-2">
                  No previous chat history.
                </div>
              ) : (
                sessions.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => setCurrentSessionId(s.id)}
                    className={`group p-2.5 rounded-lg cursor-pointer flex items-center justify-between gap-2 transition-all border ${currentSessionId === s.id
                        ? 'bg-raxel-violet-soft border-raxel-violet-muted shadow-2xs'
                        : 'bg-transparent border-transparent hover:bg-raxel-surface-subtle'
                      }`}
                  >
                    <div className="flex flex-col overflow-hidden">
                      <span
                        className={`text-xs truncate ${currentSessionId === s.id
                            ? 'font-semibold text-raxel-indigo'
                            : 'font-medium text-raxel-ink'
                          }`}
                      >
                        {s.title}
                      </span>
                      <span className="text-[10px] text-raxel-faint flex items-center gap-1 mt-0.5">
                        <Clock className="w-2.5 h-2.5" /> {s.timestamp}
                      </span>
                    </div>

                    <button
                      onClick={(e) => handleDeleteSession(s.id, e)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-raxel-muted hover:text-status-danger-text rounded transition-all focus-visible:opacity-100 focus-visible:outline-none"
                      title="Delete conversation"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* MAIN CHAT AREA — Fixed h-[calc(100vh-64px)] viewport height */}
      <div className="flex-1 flex flex-col max-w-4xl mx-auto w-full p-4 sm:p-6 relative h-[calc(100vh-64px)] min-h-0 z-10 justify-between overflow-hidden">
        {/* Top Chat Control Bar */}
        <div className="flex flex-wrap sm:flex-nowrap justify-between items-center gap-2 pb-3.5 border-b border-raxel-border/80 mb-3 shrink-0 bg-raxel-soft-white/80 backdrop-blur-xs">
          <div className="flex flex-wrap items-center gap-2">
            {!historyOpen && (
              <Button
                variant="secondary"
                size="sm"
                icon={History}
                onClick={() => setHistoryOpen(true)}
              >
                History
              </Button>
            )}

            {/* Siri-inspired Status Badge with Pulsing Live Dot */}
            <span className="text-xs font-medium text-raxel-indigo bg-raxel-violet-soft/90 px-3 py-1 rounded-full border border-raxel-border inline-flex items-center gap-2 shadow-2xs">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-raxel-teal opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-raxel-teal"></span>
              </span>
              <ShieldCheck className="w-3.5 h-3.5 text-raxel-teal" /> Grounded RAG
            </span>

            {/* AI Provider & Model Selector */}
            <div className="flex items-center gap-1.5 bg-white px-2.5 py-1 rounded-xl border border-raxel-border shadow-2xs">
              <Cpu className="w-3.5 h-3.5 text-raxel-indigo shrink-0" />
              <select
                value={providerSettings.provider}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="text-xs font-semibold text-raxel-indigo bg-transparent outline-none cursor-pointer pr-1"
                aria-label="Select AI Provider"
              >
                {availableProvidersData?.providers ? (
                  availableProvidersData.providers.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} {p.available ? '(Ready)' : '(No Key / Offline)'}
                    </option>
                  ))
                ) : (
                  <>
                    <option value="gemini">Gemini API (Cloud)</option>
                    <option value="ollama">Local Ollama</option>
                  </>
                )}
              </select>

              <span className="text-raxel-border font-light">|</span>

              <select
                value={providerSettings.model}
                onChange={(e) => handleModelChange(e.target.value)}
                className="text-xs font-medium text-raxel-muted bg-transparent outline-none cursor-pointer max-w-[140px] truncate"
                aria-label="Select Model"
              >
                {((availableProvidersData?.providers?.find((p) => p.id === providerSettings.provider)?.models) || DEFAULT_PROVIDER_MODELS[providerSettings.provider] || []).map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <Button
            variant="secondary"
            size="sm"
            icon={Plus}
            onClick={handleNewChat}
          >
            New Chat
          </Button>
        </div>

        {/* Messages Feed */}
        <div className="flex-1 overflow-y-auto pr-1 flex flex-col gap-4 pb-4 min-h-0">
          {messages.length === 0 ? (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="mt-4 sm:mt-6 mb-auto text-left max-w-2xl w-full self-center"
            >
              <div className="bg-white/90 backdrop-blur-md border border-raxel-border/90 rounded-2xl shadow-md hover:shadow-lg transition-all duration-300 p-6 sm:p-8 relative overflow-hidden">
                {/* Subtle AI Card Top Shimmer */}
                <div className="absolute top-0 left-0 right-0 h-[2px] bg-gradient-to-r from-raxel-teal via-raxel-indigo to-raxel-violet" />

                <div className="flex items-center gap-2 mb-2.5">
                  <span className="text-[11px] font-medium tracking-wider text-raxel-indigo uppercase bg-raxel-violet-soft px-2.5 py-0.5 rounded-full border border-raxel-border inline-flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3 text-raxel-teal" />
                    COLLEGE KNOWLEDGE ASSISTANT
                  </span>
                </div>

                <h1 className="text-2xl sm:text-3xl font-semibold text-raxel-indigo tracking-tight mb-2 flex items-center gap-2">
                  What do you want to know?
                </h1>

                <p className="text-xs sm:text-sm text-raxel-muted mb-6 leading-relaxed">
                  Ask RAXEL about verified academic regulations, handbooks, placement criteria, and hostel policies.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {EXAMPLE_PROMPTS.map((prompt, idx) => (
                    <motion.button
                      key={idx}
                      whileHover={{ scale: loading ? 1 : 1.015, y: loading ? 0 : -2 }}
                      whileTap={{ scale: loading ? 1 : 0.98 }}
                      onClick={() => !loading && handleSend(prompt)}
                      disabled={loading}
                      className="p-3.5 text-left rounded-xl border border-raxel-border bg-raxel-soft-white/80 hover:bg-white text-xs sm:text-sm text-raxel-ink hover:text-raxel-indigo hover:border-raxel-indigo/40 hover:shadow-sm transition-all duration-200 flex items-center justify-between gap-2.5 group focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-raxel-indigo/20 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <div className="flex items-center gap-2.5">
                        <MessageSquareQuote className="w-4 h-4 text-raxel-indigo shrink-0 transition-transform group-hover:scale-110" />
                        <span className="font-medium">{prompt}</span>
                      </div>
                      <ArrowUpRight className="w-4 h-4 text-raxel-faint group-hover:text-raxel-indigo shrink-0 transition-all duration-200 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                    </motion.button>
                  ))}
                </div>
              </div>
            </motion.div>
          ) : (
            messages.map((msg, idx) => (
              <ChatMessage
                key={idx}
                msg={msg}
                idx={idx}
                isLast={idx === messages.length - 1}
                isCopied={copiedIndex === idx}
                onCopy={handleCopyText}
                onRegenerate={handleRegenerate}
              />
            ))
          )}

          {loading && (
            <div className="flex flex-col gap-2">
              <RaxelSearchAnimation />
              <div className="text-center text-xs text-raxel-teal font-medium animate-pulse">
                Synthesizing grounded response from verified documents...
              </div>
            </div>
          )}

          {error && (
            <Alert type="error" message={error} onClose={() => setError('')} />
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* CHAT COMPOSER — Anchored sticky to bottom of viewport, fixed position, no content overlap */}
        <div className="sticky bottom-0 shrink-0 pt-2 pb-2 bg-raxel-soft-white/95 backdrop-blur-md z-30 w-full mt-auto">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="flex gap-2.5 items-center bg-white p-2.5 sm:p-3 rounded-2xl border border-raxel-border/90 shadow-md hover:shadow-lg focus-within:border-raxel-indigo focus-within:ring-4 focus-within:ring-raxel-indigo/10 focus-within:shadow-[0_4px_25px_rgba(99,102,241,0.15)] transition-all duration-300"
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={loading ? "RAXEL is synthesizing answer..." : "Ask RAXEL..."}
              disabled={loading}
              rows={1}
              className="flex-1 border-none outline-none resize-none text-xs sm:text-sm font-sans px-2 bg-transparent text-raxel-ink placeholder:text-raxel-muted/70 max-h-28 leading-relaxed disabled:opacity-60"
            />

            {/* CHAT BUTTON — Prominent, anchored at bottom right of composer */}
            <motion.div whileHover={{ scale: loading ? 1 : 1.05 }} whileTap={{ scale: loading ? 1 : 0.95 }}>
              <Button
                onClick={() => handleSend()}
                disabled={loading || !input.trim()}
                isLoading={loading}
                variant="primary"
                size="sm"
                icon={Send}
                className="shrink-0 !p-2.5 min-h-[40px] w-[40px] rounded-xl shadow-sm hover:shadow-md transition-all"
                aria-label="Send question"
              />
            </motion.div>
          </motion.div>

          <div className="text-center mt-2 shrink-0">
            <span className="text-[11px] text-raxel-faint font-normal">
              RAXEL answers are grounded in official verified college documents.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
