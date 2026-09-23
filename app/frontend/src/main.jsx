import React from "react";
import { createRoot } from "react-dom/client";
import { Activity, ArrowUp, FileText, LogIn, LogOut, Paperclip, Send, ShieldCheck, Trash2, Upload, UserPlus, X } from "lucide-react";
import "./styles.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function apiFetch(path, options = {}, token = "") {
  const headers = new Headers(options.headers || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || payload.message || "Request failed");
  return payload;
}

function App() {
  const [token, setToken] = React.useState(() => localStorage.getItem("assistant_token") || "");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [message, setMessage] = React.useState("");
  const [messages, setMessages] = React.useState([]);
  const [files, setFiles] = React.useState([]);
  const [selectedFiles, setSelectedFiles] = React.useState([]);
  const [status, setStatus] = React.useState("Checking API");
  const [error, setError] = React.useState("");
  const [busy, setBusy] = React.useState(false);

  React.useEffect(() => {
    apiFetch("/health").then(() => setStatus("API online")).catch(() => setStatus("API unavailable"));
  }, []);

  React.useEffect(() => {
    if (!token) return;
    apiFetch("/rag/files", {}, token).then((data) => setFiles(data.files || [])).catch(() => setFiles([]));
  }, [token]);

  async function authenticate(path) {
    setError(""); setBusy(true);
    try {
      const data = await apiFetch(path, { method: "POST", body: JSON.stringify({ email, password }) });
      if (path.endsWith("login")) {
        localStorage.setItem("assistant_token", data.access_token);
        setToken(data.access_token); setPassword("");
      } else setStatus("Account created");
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  async function sendMessage(event) {
    event.preventDefault();
    if (!message.trim() || !token) return;
    const text = message.trim(); setMessage(""); setError("");
    setMessages((current) => [...current, { role: "user", text }]); setBusy(true);
    try {
      const data = await apiFetch("/chat/", { method: "POST", body: JSON.stringify({ message: text }) }, token);
      setMessages((current) => [...current, { role: "assistant", text: data.reply }]);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  async function uploadFiles(event) {
    event.preventDefault(); if (!selectedFiles.length || !token) return;
    const body = new FormData(); selectedFiles.forEach((file) => body.append("files", file));
    setBusy(true); setError("");
    try {
      await apiFetch("/rag/upload", { method: "POST", body }, token);
      setSelectedFiles([]); event.target.reset();
      const data = await apiFetch("/rag/files", {}, token); setFiles(data.files || []);
    } catch (err) { setError(err.message); } finally { setBusy(false); }
  }

  async function deleteFile(filename) {
    try {
      await apiFetch(`/rag/files/${encodeURIComponent(filename)}`, { method: "DELETE" }, token);
      setFiles((current) => current.filter((file) => file.filename !== filename));
    } catch (err) { setError(err.message); }
  }

  function logout() { localStorage.removeItem("assistant_token"); setToken(""); setMessages([]); setFiles([]); }

  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark">PA</span><div><p className="eyebrow">PERSONAL SYSTEM</p><h1>Personal assistant</h1></div></div>
      <div className="topbar-actions"><span className={`status ${status === "API online" ? "is-online" : ""}`}><Activity size={14} />{status}</span>{token && <button className="icon-button" onClick={logout} title="Sign out"><LogOut size={17} /></button>}</div>
    </header>
    <main className="workspace">
      {!token ? <section className="auth-panel">
        <div className="intro"><p className="eyebrow">PRIVATE WORKSPACE</p><h2>A calmer place to think.</h2><p>Connect your account to chat with your assistant and give it documents to remember.</p><div className="trust"><ShieldCheck size={17} /><span>Your session is secured with a Supabase bearer token.</span></div></div>
        <div className="auth-form"><div className="section-heading"><span>01</span><h3>Sign in or create an account</h3></div><label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" /></label><label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="At least 8 characters" /></label><div className="form-actions"><button onClick={() => authenticate("/auth/login")} disabled={busy || !email || !password}><LogIn size={16} />Sign in</button><button className="button-secondary" onClick={() => authenticate("/auth/signup")} disabled={busy || !email || !password}><UserPlus size={16} />Create account</button></div></div>
      </section> : <div className="dashboard">
        <section className="chat-panel"><div className="panel-header"><div><p className="eyebrow">CONVERSATION</p><h2>What's on your mind?</h2></div><span className="live-dot">LIVE</span></div><div className="message-list">{messages.length === 0 && <div className="empty-state"><span className="empty-icon"><Send size={18} /></span><h3>Start with a thought</h3><p>Ask for a plan, a summary, or a next step.</p></div>}{messages.map((item, index) => <div className={`message ${item.role}`} key={`${item.role}-${index}`}><span>{item.role === "user" ? "YOU" : "ASSISTANT"}</span><p>{item.text}</p></div>)}</div><form className="composer" onSubmit={sendMessage}><textarea value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Write a message..." rows="2" onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(event); } }} /><button className="send-button" disabled={busy || !message.trim()} title="Send message"><ArrowUp size={19} /></button></form></section>
        <aside className="side-panel"><div className="panel-header compact"><div><p className="eyebrow">MEMORY</p><h2>Your documents</h2></div><FileText size={19} /></div><form className="upload-area" onSubmit={uploadFiles}><input id="file-picker" type="file" multiple onChange={(event) => setSelectedFiles(Array.from(event.target.files || []))} /><label htmlFor="file-picker"><Upload size={20} /><strong>{selectedFiles.length ? `${selectedFiles.length} file${selectedFiles.length > 1 ? "s" : ""} selected` : "Add reference files"}</strong><span>PDF, text, or other supported files</span></label><button type="submit" disabled={busy || !selectedFiles.length}><Paperclip size={15} />Upload files</button></form><div className="file-list">{files.length === 0 ? <p className="muted">No files uploaded yet.</p> : files.map((file) => <div className="file-row" key={file.filename}><FileText size={16} /><span title={file.filename}>{file.filename}</span><button className="delete-button" onClick={() => deleteFile(file.filename)} title={`Delete ${file.filename}`}><Trash2 size={15} /></button></div>)}</div></aside>
      </div>}
      {error && <div className="error-toast" role="alert"><X size={16} />{error}<button onClick={() => setError("")} title="Dismiss"><X size={14} /></button></div>}
    </main>
  </div>;
}

createRoot(document.getElementById("root")).render(<React.StrictMode><App /></React.StrictMode>);
