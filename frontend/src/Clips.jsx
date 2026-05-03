import { useState, useRef, useEffect, useCallback } from 'react';
import { processClips, deleteClips, getAllClips } from './api';

const STEPS = [
  { id: 'fetch',   label: 'Fetching video info…'       },
  { id: 'dl',      label: 'Downloading from YouTube…'  },
  { id: 'split',   label: 'Splitting into clips…'       },
  { id: 'shorts',  label: 'Converting to Shorts (9:16)…'},
  { id: 'labels',  label: 'Adding part labels…'         },
  { id: 'done',    label: 'All done!'                   },
];

function useStepCycle(active) {
  const [step, setStep] = useState(0);
  const ref = useRef(null);

  useEffect(() => {
    if (!active) { setStep(0); return; }
    ref.current = setInterval(() => {
      setStep(s => Math.min(s + 1, STEPS.length - 2));
    }, 4500);
    return () => clearInterval(ref.current);
  }, [active]);

  return step;
}

function VideoCard({ url, index, total, videoId, onDelete, readOnly }) {
  const [copied, setCopied] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
  const src = url.startsWith('http') ? url : `${baseUrl}${url}`;

  const copy = () => {
    navigator.clipboard.writeText(src);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDelete = async () => {
    if (!confirm('Delete all clips for this video?')) return;
    setDeleting(true);
    try {
      await deleteClips(videoId);
      onDelete(videoId);
    } catch {
      setDeleting(false);
    }
  };

  return (
    <div className="clip-card" style={{ animationDelay: `${index * 80}ms` }}>
      <div className="clip-badge">Part {index + 1}/{total}</div>
      <video className="clip-video" src={src} controls preload="metadata" playsInline>
        <track kind="captions" />
      </video>
      <div className="clip-actions">
        <button className="clip-copy-btn" onClick={copy}>
          {copied ? '✅ Copied!' : '🔗 Copy Link'}
        </button>
        {!readOnly && index === 0 && (
          <button className="clip-delete-btn" onClick={handleDelete} disabled={deleting}>
            {deleting ? '…' : '🗑️'}
          </button>
        )}
      </div>
    </div>
  );
}

VideoCard.propTypes = {};

/* ── Library tab ─────────────────────────────────────────────── */
function Library() {
  const [data, setData] = useState(null);   // null = loading, object = loaded
  const [error, setError] = useState('');
  const [preview, setPreview] = useState(null); // { videoId, links }

  const load = useCallback(async () => {
    setData(null);
    setError('');
    try {
      const res = await getAllClips();
      setData(res);
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to load');
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (error) return (
    <div className="clips-error" style={{ marginTop: 32 }}>
      <span>❌</span><span>{error}</span>
      <button onClick={load}>Retry</button>
    </div>
  );

  if (!data) return (
    <div className="clips-loading" style={{ paddingTop: 60 }}>
      <div className="clips-loading-ring">
        <div className="clips-loading-ring-inner" />
        <span className="clips-loading-ring-icon">▶</span>
      </div>
      <p style={{ color: 'var(--muted)' }}>Loading library…</p>
    </div>
  );

  if (data.videos.length === 0) return (
    <div className="clips-empty">
      <div className="clips-empty-icon">📂</div>
      <p>No clips stored yet.</p>
      <p className="clips-empty-sub">Generate some clips using the <strong>Generate</strong> tab.</p>
    </div>
  );

  return (
    <div className="library-wrap">
      {/* Summary bar */}
      <div className="library-summary">
        <div className="library-stat">
          <span className="library-stat-num">{data.total_videos}</span>
          <span className="library-stat-label">Videos</span>
        </div>
        <div className="library-stat-div" />
        <div className="library-stat">
          <span className="library-stat-num">{data.total_clips}</span>
          <span className="library-stat-label">Total Clips</span>
        </div>
        <button className="library-refresh-btn" onClick={load} title="Refresh">↻</button>
      </div>

      {/* Video rows */}
      {data.videos.map((v) => (
        <div key={v.video_id} className="clips-group">
          <div className="clips-group-header">
            <span className="clips-group-id">📁 {v.video_id}</span>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span className="clips-group-count">{v.total} clips</span>
              <button
                className="library-preview-btn"
                onClick={() => setPreview(prev => prev?.videoId === v.video_id ? null : { videoId: v.video_id, links: v.links })}
              >
                {preview?.videoId === v.video_id ? '▲ Hide' : '▼ Preview'}
              </button>
            </div>
          </div>

          {/* Clip thumbnails row (always visible) */}
          <div className="library-thumb-row">
            {v.links.map((link, i) => {
              const baseUrl = import.meta.env.VITE_API_BASE_URL || '';
              const src = link.startsWith('http') ? link : `${baseUrl}${link}`;
              return (
                <button
                  key={link}
                  className={`library-thumb ${preview?.videoId === v.video_id ? 'library-thumb-active' : ''}`}
                  onClick={() => setPreview({ videoId: v.video_id, links: v.links })}
                  title={`Part ${i + 1}`}
                >
                  <video src={src} preload="none" className="library-thumb-video">
                    <track kind="captions" />
                  </video>
                  <span className="library-thumb-label">Part {i + 1}</span>
                </button>
              );
            })}
          </div>

          {/* Expanded preview grid */}
          {preview?.videoId === v.video_id && (
            <div className="clips-grid" style={{ marginTop: 16 }}>
              {v.links.map((link, i) => (
                <VideoCard
                  key={link}
                  url={link}
                  index={i}
                  total={v.total}
                  videoId={v.video_id}
                  onDelete={() => {}}
                  readOnly
                />
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

/* ── Main ─────────────────────────────────────────────────────── */
function stepClass(i, current) {
  if (i < current) return 'clips-step-done';
  if (i === current) return 'clips-step-active';
  return 'clips-step-pending';
}

export default function Clips() {
  const [tab, setTab] = useState('generate'); // 'generate' | 'library'
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState('idle');
  const [error, setError] = useState('');
  const [groups, setGroups] = useState([]);
  const stepIndex = useStepCycle(status === 'loading');

  const submit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    setStatus('loading');
    setError('');
    try {
      const results = await processClips([url.trim()]);
      const newGroups = (results.clips || []).map(c => ({ videoId: c.video_id, links: c.links }));
      setGroups(prev => {
        const ids = new Set(newGroups.map(g => g.videoId));
        return [...newGroups, ...prev.filter(g => !ids.has(g.videoId))];
      });
      setStatus('done');
      setUrl('');
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Something went wrong');
      setStatus('error');
    }
  };

  const removeGroup = (videoId) => setGroups(prev => prev.filter(g => g.videoId !== videoId));
  const totalClips = groups.reduce((s, g) => s + g.links.length, 0);

  return (
    <div className="clips-page">
      {/* Hero */}
      <div className="clips-hero">
        <div className="clips-hero-glow" />
        <h1 className="clips-hero-title">
          <span className="clips-hero-yt">▶</span> YouTube → Shorts
        </h1>
        <p className="clips-hero-sub">
          Paste any YouTube link — we'll split it into vertical 9:16 clips ready to post.
        </p>

        {tab === 'generate' && (
          <form className="clips-form" onSubmit={submit}>
            <div className="clips-input-wrap">
              <span className="clips-input-icon">🔗</span>
              <input
                className="clips-input"
                type="url"
                placeholder="https://youtube.com/watch?v=..."
                value={url}
                onChange={e => setUrl(e.target.value)}
                disabled={status === 'loading'}
                required
              />
            </div>
            <button
              type="submit"
              className="clips-submit-btn"
              disabled={status === 'loading' || !url.trim()}
            >
              {status === 'loading' ? <span className="clips-btn-spinner" /> : '✂️ Generate Clips'}
            </button>
          </form>
        )}
      </div>

      {/* Tab switcher */}
      <div className="clips-tabs">
        <button
          className={`clips-tab-btn ${tab === 'generate' ? 'clips-tab-active' : ''}`}
          onClick={() => setTab('generate')}
        >
          ✂️ Generate
        </button>
        <button
          className={`clips-tab-btn ${tab === 'library' ? 'clips-tab-active' : ''}`}
          onClick={() => setTab('library')}
        >
          📂 Library
        </button>
      </div>

      {/* ── GENERATE TAB ── */}
      {tab === 'generate' && (
        <>
          {status === 'loading' && (
            <div className="clips-loading">
              <div className="clips-loading-ring">
                <div className="clips-loading-ring-inner" />
                <span className="clips-loading-ring-icon">▶</span>
              </div>
              <div className="clips-steps">
                {STEPS.slice(0, -1).map((s, i) => (
                  <div key={s.id} className={`clips-step ${stepClass(i, stepIndex)}`}>
                    <span className="clips-step-dot" />
                    {s.label}
                  </div>
                ))}
              </div>
            </div>
          )}

          {status === 'error' && (
            <div className="clips-error">
              <span>❌</span><span>{error}</span>
              <button onClick={() => setStatus('idle')}>Dismiss</button>
            </div>
          )}

          {groups.length > 0 && (
            <div className="clips-results">
              <div className="clips-results-header">
                <h2 className="clips-results-title">
                  🎬 {totalClips} {totalClips === 1 ? 'Clip' : 'Clips'} Generated
                </h2>
              </div>
              {groups.map(({ videoId, links }) => (
                <div key={videoId} className="clips-group">
                  <div className="clips-group-header">
                    <span className="clips-group-id">📁 {videoId}</span>
                    <span className="clips-group-count">{links.length} clips</span>
                  </div>
                  <div className="clips-grid">
                    {links.map((link, i) => (
                      <VideoCard key={link} url={link} index={i} total={links.length} videoId={videoId} onDelete={removeGroup} readOnly={false} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {status !== 'loading' && groups.length === 0 && status !== 'error' && (
            <div className="clips-empty">
              <div className="clips-empty-icon">🎬</div>
              <p>Paste a YouTube URL above and hit <strong>Generate Clips</strong></p>
              <p className="clips-empty-sub">Videos are automatically split into 45–60 second vertical shorts</p>
            </div>
          )}
        </>
      )}

      {/* ── LIBRARY TAB ── */}
      {tab === 'library' && <Library />}
    </div>
  );
}
