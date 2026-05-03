import { useState, useRef } from 'react';
import { uploadCookies } from './api';

export default function Settings() {
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null); // null | 'loading' | 'success' | 'error'
  const [message, setMessage] = useState('');
  const inputRef = useRef(null);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setStatus(null);
      setMessage('');
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const dropped = e.dataTransfer.files[0];
    if (dropped) {
      setFile(dropped);
      setStatus(null);
      setMessage('');
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setStatus('loading');
    setMessage('');
    try {
      const result = await uploadCookies(file);
      setStatus('success');
      setMessage(`Cookies saved to: ${result.cookies_file}`);
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
    } catch (err) {
      setStatus('error');
      setMessage(err.response?.data?.detail || err.message || 'Upload failed');
    }
  };

  return (
    <div className="page">
      <header className="hero" style={{ marginBottom: 32 }}>
        <div>
          <h1 className="hero-title">⚙️ Settings</h1>
          <p className="hero-sub">Upload your YouTube <code>cookies.txt</code> to bypass bot detection</p>
        </div>
      </header>

      <section className="card" style={{ maxWidth: 560 }}>
        <h2 style={{ marginTop: 0, fontSize: 18 }}>YouTube Cookies</h2>
        <p style={{ color: 'var(--muted)', fontSize: 14, marginBottom: 20 }}>
          Export your cookies from YouTube using the <strong>"Get cookies.txt LOCALLY"</strong> Chrome extension,
          then upload the file here. This allows the server to download age-restricted or
          bot-protected YouTube videos.
        </p>

        {/* Drop zone */}
        <button
          type="button"
          className="cookies-dropzone"
          onClick={() => inputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
          style={{ width: '100%', font: 'inherit' }}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".txt,text/plain"
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          {file ? (
            <div className="cookies-dropzone-selected">
              <span className="cookies-file-icon">📄</span>
              <span className="cookies-file-name">{file.name}</span>
              <span className="cookies-file-size">({(file.size / 1024).toFixed(1)} KB)</span>
            </div>
          ) : (
            <div className="cookies-dropzone-empty">
              <span style={{ fontSize: 36 }}>🍪</span>
              <p>Drop <code>cookies.txt</code> here or <u>click to browse</u></p>
            </div>
          )}
        </button>

        {/* Status message */}
        {status === 'success' && (
          <div className="cookies-msg cookies-msg--success">✅ {message}</div>
        )}
        {status === 'error' && (
          <div className="cookies-msg cookies-msg--error">❌ {message}</div>
        )}

        <button
          className="btn-primary"
          onClick={handleUpload}
          disabled={!file || status === 'loading'}
          style={{ marginTop: 16, width: '100%' }}
        >
          {status === 'loading' ? 'Uploading…' : 'Upload cookies.txt'}
        </button>

        <details style={{ marginTop: 24 }}>
          <summary style={{ cursor: 'pointer', color: 'var(--muted)', fontSize: 13 }}>
            How to get cookies.txt
          </summary>
          <ol style={{ fontSize: 13, color: 'var(--muted)', paddingLeft: 20, marginTop: 8 }}>
            <li>Install <strong>"Get cookies.txt LOCALLY"</strong> from the Chrome Web Store</li>
            <li>Open <strong>youtube.com</strong> and make sure you are logged in</li>
            <li>Click the extension icon → <strong>Export</strong></li>
            <li>Save the file as <code>cookies.txt</code></li>
            <li>Upload it here</li>
          </ol>
        </details>
      </section>
    </div>
  );
}
