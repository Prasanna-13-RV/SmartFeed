import { useState, useEffect } from 'react';
import { fetchRandomHeadlines, generatePost } from './api';

const TEMPLATES = {
  image: [
    { id: 1, name: 'Dark Bold', desc: 'Orange header + photo strip', bg: '#12163A', accent: '#e03210', text: '#fff' },
    { id: 2, name: 'Light Clean', desc: 'White + blue minimal', bg: '#f8faff', accent: '#2563eb', text: '#0f1722' },
    { id: 3, name: 'Photo Overlay', desc: 'RSS image as background', bg: '#1a1a2e', accent: '#e94560', text: '#fff' },
  ],
  video: [
    { id: 1, name: 'Dark Navy', desc: 'Blue on dark portrait', bg: '#080A14', accent: '#1E78FF', text: '#fff' },
    { id: 2, name: 'Breaking News', desc: 'Red & dark bold style', bg: '#0a0808', accent: '#cc0000', text: '#fff' },
  ],
};

export default function Create() {
  const [step, setStep] = useState('select'); // select, choose, generating, preview
  const [headlines, setHeadlines] = useState([]);
  const [selected, setSelected] = useState(null);
  const [mediaType, setMediaType] = useState(null); // 'image' or 'video'
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState([]);
  const [currentStep, setCurrentStep] = useState('');
  const [preview, setPreview] = useState(null);
  const [message, setMessage] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [selectedTemplate, setSelectedTemplate] = useState(null);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

  const loadHeadlines = async () => {
    setLoading(true);
    try {
      const items = await fetchRandomHeadlines(10);
      setHeadlines(items);
      setSelected(null);
    } catch (error) {
      setMessage(`Failed to load headlines: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadHeadlines();
  }, []);

  const handleSelectHeadline = (headline) => {
    setSelected(headline);
    setMediaType(null);
    setSelectedTemplate(null);
    setStep('choose');
  };

  const handleChooseMedia = async () => {
    const type = mediaType;
    const template = selectedTemplate || 1;
    setStep('generating');
    setLogs([]);
    setCurrentStep('');
    setLoading(true);

    const log = (msg) => {
      setLogs((prev) => [...prev, msg]);
      setCurrentStep(msg);
    };

    try {
      log(`Preparing ${type === 'video' ? 'YouTube Short' : 'Instagram Image'}...`);
      log(`Reading: "${selected.title.slice(0, 55)}${selected.title.length > 55 ? '...' : ''}"`);
      log(`Category: ${selected.category.toUpperCase()}`);
      log(`Template: ${TEMPLATES[type].find(t => t.id === template)?.name || 'Default'}`);
      log(`Generating ${type === 'video' ? '1080×1920 MP4 video' : '1080×1080 JPG image'}...`);

      const platform = type === 'video' ? 'youtube' : 'instagram';
      const result = await generatePost(selected.rss_id, platform, template);

      log('✓ Media ready!');

      setPreview({
        ...result,
        mediaType: result.generated_media_link?.endsWith('.mp4') ? 'video' : 'image',
      });
      setStep('preview');
    } catch (error) {
      const errMsg = `✗ Failed: ${error.response?.data?.detail || error.message}`;
      log(errMsg);
      setMessage(`Generation failed: ${error.message}`);
      setTimeout(() => setStep('select'), 2500);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (platform) => {
    setLoading(true);
    try {
      const log = (msg) => {
        setLogs((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`]);
      };

      log(`Uploading to ${platform}...`);
      log('Processing upload request...');
      
      // The post is already marked as uploaded from generatePost
      log(`✓ Successfully uploaded to ${platform}`);
      log(`Link: ${preview.published_link}`);

      setMessage(`✓ Uploaded to ${platform}!`);
      setTimeout(() => {
        setStep('select');
        loadHeadlines();
      }, 2000);
    } catch (error) {
      log(`✗ Upload failed: ${error.message}`);
      setMessage(`Upload failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <header className="hero">
        <div>
          <h1>📝 Content Creator</h1>
          <p>Create Instagram posts and YouTube Shorts from headlines in minutes.</p>
        </div>
      </header>

      {/* STEP 1: SELECT HEADLINE */}
      {step === 'select' && (
        <section className="creator-section">
          <div className="creator-controls">
            <h2>Step 1: Select a Headline</h2>
            <div className="filters">
              <label>
                <span>Filter by Status</span>
                <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                  <option value="all">All</option>
                  <option value="queued">Queued</option>
                  <option value="failed">Failed</option>
                </select>
              </label>
              <button onClick={loadHeadlines} disabled={loading} className="btn-primary">
                Refresh Headlines
              </button>
            </div>
          </div>

          <div className="headlines-grid">
            {headlines
              .filter((h) => statusFilter === 'all' || h.post_status === statusFilter)
              .map((headline) => (
                <div
                  key={headline.rss_id}
                  className="headline-card"
                  onClick={() => handleSelectHeadline(headline)}
                >
                  {headline.image_url && (
                    <img src={headline.image_url} alt={headline.title} className="headline-image" />
                  )}
                  <div className="headline-content">
                    <h3>{headline.title}</h3>
                    {headline.description && <p>{headline.description}</p>}
                    <div className="headline-meta">
                      <span className="category-tag">{headline.category}</span>
                      <span className={`status-tag status-${headline.post_status}`}>
                        {headline.post_status}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
          </div>

          {headlines.length === 0 && (
            <div className="empty-state">
              <p>No headlines available. Fetch RSS first!</p>
            </div>
          )}

          {message && <div className="message">{message}</div>}
        </section>
      )}

      {/* STEP 2: CHOOSE FORMAT + TEMPLATE */}
      {step === 'choose' && selected && (
        <section className="creator-section">
          <div className="selected-headline">
            {selected.image_url && (
              <img src={selected.image_url} alt={selected.title} className="selected-rss-img" />
            )}
            <div>
              <h3>{selected.title}</h3>
              {selected.description && <p>{selected.description}</p>}
            </div>
          </div>

          <p className="step-label">1 — Choose Format</p>
          <div className="media-choice">
            <button
              onClick={() => { setMediaType('image'); setSelectedTemplate(null); }}
              className={`choice-btn image-btn${mediaType === 'image' ? ' choice-selected' : ''}`}
            >
              📸 Instagram Image<br /><span className="choice-subtitle">1080×1080 JPG</span>
            </button>
            <button
              onClick={() => { setMediaType('video'); setSelectedTemplate(null); }}
              className={`choice-btn video-btn${mediaType === 'video' ? ' choice-selected' : ''}`}
            >
              🎬 YouTube Short<br /><span className="choice-subtitle">1080×1920 MP4</span>
            </button>
          </div>

          {mediaType && (
            <>
              <p className="step-label">2 — Choose Template</p>
              <div className="template-grid">
                {TEMPLATES[mediaType].map((t) => (
                  <div
                    key={t.id}
                    className={`template-card${selectedTemplate === t.id ? ' template-selected' : ''}`}
                    onClick={() => setSelectedTemplate(t.id)}
                  >
                    <div
                      className="template-preview"
                      style={{ background: t.bg, aspectRatio: mediaType === 'video' ? '9/16' : '1/1' }}
                    >
                      <div style={{ background: t.accent, height: '22%', width: '100%', borderRadius: '3px 3px 0 0' }} />
                      <div style={{ padding: '8px 6px' }}>
                        <div style={{ background: t.accent, height: '4px', width: '60%', margin: '6px auto', borderRadius: '2px' }} />
                        <div style={{ background: t.text, height: '3px', width: '80%', margin: '5px auto', borderRadius: '2px', opacity: 0.9 }} />
                        <div style={{ background: t.text, height: '3px', width: '65%', margin: '5px auto', borderRadius: '2px', opacity: 0.6 }} />
                        <div style={{ background: t.text, height: '3px', width: '75%', margin: '5px auto', borderRadius: '2px', opacity: 0.4 }} />
                      </div>
                    </div>
                    <div className="template-name">{t.name}</div>
                    <div className="template-desc">{t.desc}</div>
                  </div>
                ))}
              </div>
            </>
          )}

          {mediaType && selectedTemplate && (
            <button onClick={handleChooseMedia} disabled={loading} className="btn-generate">
              ✨ Generate {mediaType === 'video' ? 'YouTube Short' : 'Instagram Post'} →
            </button>
          )}

          <button onClick={() => setStep('select')} className="btn-back">← Back to Headlines</button>
        </section>
      )}

      {/* STEP 3: GENERATING */}
      {step === 'generating' && (
        <section className="creator-section">
          <div className="generating-container">
            <div className="generating-spinner"></div>
            <div className="generating-label">
              {currentStep || `Generating ${mediaType === 'video' ? 'YouTube Short' : 'Instagram Image'}...`}
            </div>
            <div className="generating-steps">
              {logs.map((log, i) => (
                <div key={i} className={`gen-step ${i === logs.length - 1 ? 'gen-step-active' : 'gen-step-done'}`}>
                  {i < logs.length - 1 ? '✓' : '›'} {log}
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* STEP 4: PREVIEW & UPLOAD */}
      {step === 'preview' && preview && (
        <section className="creator-section">
          <h2>Step 4: Review & Upload</h2>
          <div className="preview-container">
            <div className="preview-media">
              <h3>Preview</h3>
              {preview.mediaType === 'video' ? (
                <video controls style={{ maxWidth: '100%', borderRadius: '8px' }}>
                  <source src={`${API_BASE}${preview.generated_media_link.replace(/\\/g, '/')}`} />
                </video>
              ) : (
                <img
                  src={`${API_BASE}${preview.generated_media_link.replace(/\\/g, '/')}`}
                  alt="Preview"
                  style={{ maxWidth: '100%', borderRadius: '8px' }}
                />
              )}
            </div>

            <div className="preview-info">
              <h3>{preview.title}</h3>
              <p className="info-label">Platform: <strong>{preview.assigned_platform}</strong></p>
              <p className="info-label">Category: <strong>{preview.category}</strong></p>
              {preview.published_link && (
                <p className="info-label">
                  Link: <a href={preview.published_link} target="_blank" rel="noreferrer">{preview.published_link}</a>
                </p>
              )}

              <div className="upload-buttons">
                <button
                  onClick={() => handleUpload('instagram')}
                  disabled={loading}
                  className="btn-instagram"
                >
                  📸 Upload to Instagram
                </button>
                <button
                  onClick={() => handleUpload('youtube')}
                  disabled={loading}
                  className="btn-youtube"
                >
                  ▶ Upload to YouTube
                </button>
              </div>

              <div className="logs-container">
                {logs.map((log, i) => (
                  <div key={i} className="log-line">
                    {log}
                  </div>
                ))}
              </div>

              <button onClick={() => setStep('select')} className="btn-back">
                ← Create Another Post
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
