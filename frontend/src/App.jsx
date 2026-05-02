import { useMemo, useState, useEffect } from 'react';
import {
  fetchPosts,
  fetchRandomHeadlines,
  generateBatch,
  generatePost,
  processRss,
  retryPost,
  uploadSelected,
  fetchDbStatus,
} from './api';
import Create from './Create';

function Dashboard() {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [dbConnected, setDbConnected] = useState(null);
  const [platformFilter, setPlatformFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;
  const [headlineCount, setHeadlineCount] = useState(5);
  const [headlinePool, setHeadlinePool] = useState([]);
  const [selectedHeadlines, setSelectedHeadlines] = useState({});

  const loadPosts = async () => {
    setLoading(true);
    try {
      const items = await fetchPosts();
      setPosts(items);
    } catch (error) {
      setMessage(`Failed to load posts: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPosts();
  }, []);

  useEffect(() => {
    let interval;
    const checkStatus = async () => {
      try {
        const status = await fetchDbStatus();
        setDbConnected(status.mongo_connected);
        if (status.mongo_connected) {
          clearInterval(interval);
        }
      } catch {
        setDbConnected(false);
      }
    };
    checkStatus();
    interval = setInterval(checkStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const stats = useMemo(() => {
    return posts.reduce(
      (acc, post) => {
        acc.total += 1;
        acc[post.assigned_platform] += 1;
        acc[post.post_status] = (acc[post.post_status] || 0) + 1;
        return acc;
      },
      {
        total: 0,
        instagram: 0,
        youtube: 0,
        queued: 0,
        uploaded: 0,
        failed: 0,
      }
    );
  }, [posts]);

  const filteredPosts = useMemo(() => {
    return posts.filter((post) => {
      const platformOk = platformFilter === 'all' || post.assigned_platform === platformFilter;
      const statusOk = statusFilter === 'all' || post.post_status === statusFilter;
      return platformOk && statusOk;
    });
  }, [posts, platformFilter, statusFilter]);

  const totalPages = Math.max(1, Math.ceil(filteredPosts.length / PAGE_SIZE));
  const pagedPosts = filteredPosts.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

  const runProcessRss = async () => {
    setLoading(true);
    setMessage('');
    setPage(1);
    try {
      const result = await processRss();
      setMessage(`RSS processed: inserted ${result.inserted}, duplicates ${result.skipped_duplicates}`);
      await loadPosts();
    } catch (error) {
      setMessage(`RSS processing failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const runGenerateBatch = async () => {
    setLoading(true);
    setMessage('');
    try {
      const result = await generateBatch(10);
      setMessage(`Generate done: success ${result.success}, failed ${result.failed}`);
      await loadPosts();
    } catch (error) {
      setMessage(`Batch generation failed: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const loadRandomHeadlines = async () => {
    setLoading(true);
    setMessage('');
    try {
      const items = await fetchRandomHeadlines(headlineCount);
      setHeadlinePool(items);
      setSelectedHeadlines({});
      setMessage(`Loaded ${items.length} random headlines.`);
    } catch (error) {
      setMessage(`Failed to load random headlines: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const toggleHeadline = (rssId) => {
    setSelectedHeadlines((prev) => ({ ...prev, [rssId]: !prev[rssId] }));
  };

  const uploadFromSelection = async (platform) => {
    const selectedIds = Object.keys(selectedHeadlines).filter((id) => selectedHeadlines[id]);
    if (!selectedIds.length) {
      setMessage('Select at least one headline first.');
      return;
    }

    setLoading(true);
    setMessage('');
    try {
      const result = await uploadSelected(selectedIds, platform);
      setMessage(
        `Upload request complete: uploaded ${result.uploaded}, failed ${result.failed}, skipped ${result.skipped}`
      );
      await loadPosts();
      await loadRandomHeadlines();
    } catch (error) {
      setMessage(`Selected upload failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const onGenerateSingle = async (rssId) => {
    setLoading(true);
    setMessage('');
    try {
      await generatePost(rssId);
      setMessage('Post generated and uploaded.');
      await loadPosts();
    } catch (error) {
      setMessage(`Generate failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  const onRetry = async (rssId) => {
    setLoading(true);
    setMessage('');
    try {
      await retryPost(rssId);
      setMessage('Retry completed.');
      await loadPosts();
    } catch (error) {
      setMessage(`Retry failed: ${error.response?.data?.detail || error.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      {dbConnected === false && (
        <div className="db-banner">
          MongoDB is not connected — retrying in the background&hellip;
        </div>
      )}
      <header className="hero">
        <div>
          <h1>SmartFeed Ops Dashboard</h1>
          <p>Track content queue, balance platform distribution, and recover failed uploads quickly.</p>
        </div>
        <div className="actions">
          <button onClick={runProcessRss} disabled={loading}>Fetch RSS</button>
          <button onClick={runGenerateBatch} disabled={loading}>Generate Queue</button>
          <button onClick={loadPosts} disabled={loading}>Refresh</button>
        </div>
      </header>

      <section className="cards">
        <article className="card"><h3>Total</h3><strong>{stats.total}</strong></article>
        <article className="card"><h3>Instagram</h3><strong>{stats.instagram}</strong></article>
        <article className="card"><h3>YouTube</h3><strong>{stats.youtube}</strong></article>
        <article className="card"><h3>Queued</h3><strong>{stats.queued || 0}</strong></article>
        <article className="card"><h3>Uploaded</h3><strong>{stats.uploaded || 0}</strong></article>
        <article className="card"><h3>Failed</h3><strong>{stats.failed || 0}</strong></article>
      </section>

      <section className="queue-manager">
        <h2>Queue Manager</h2>
        <p>Useful control idea: filter by platform and status to keep both channels consistently active.</p>
        <div className="filters">
          <label>
            <span>Platform</span>
            <select value={platformFilter} onChange={(e) => { setPlatformFilter(e.target.value); setPage(1); }}>
              <option value="all">All</option>
              <option value="instagram">Instagram</option>
              <option value="youtube">YouTube</option>
            </select>
          </label>
          <label>
            <span>Status</span>
            <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}>
              <option value="all">All</option>
              <option value="queued">Queued</option>
              <option value="uploaded">Uploaded</option>
              <option value="failed">Failed</option>
            </select>
          </label>
        </div>
      </section>

      <section className="queue-manager">
        <h2>Headline Picker</h2>
        <p>Fetch 5 to 10 random headlines, select what you want, then upload to one platform from the website.</p>
        <div className="filters">
          <label>
            <span>Random count</span>
            <select
              value={headlineCount}
              onChange={(e) => setHeadlineCount(Number(e.target.value))}
            >
              <option value={5}>5</option>
              <option value={6}>6</option>
              <option value={7}>7</option>
              <option value={8}>8</option>
              <option value={9}>9</option>
              <option value={10}>10</option>
            </select>
          </label>
          <div className="actions">
            <button onClick={loadRandomHeadlines} disabled={loading}>Get Random Headlines</button>
            <button onClick={() => uploadFromSelection('youtube')} disabled={loading}>Upload Selected to YouTube</button>
            <button onClick={() => uploadFromSelection('instagram')} disabled={loading}>Upload Selected to Instagram</button>
          </div>
        </div>
        <div className="headline-list">
          {headlinePool.map((item) => (
            <label key={item.rss_id} className="headline-item">
              <input
                type="checkbox"
                checked={!!selectedHeadlines[item.rss_id]}
                onChange={() => toggleHeadline(item.rss_id)}
              />
              <span>{item.title}</span>
            </label>
          ))}
          {!headlinePool.length && <p>No random headlines loaded yet.</p>}
        </div>
      </section>

      {message && <div className="message">{message}</div>}

      <section className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Platform</th>
              <th>Status</th>
              <th>Link</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {pagedPosts.map((post) => (
              <tr key={post.rss_id}>
                <td>{post.title}</td>
                <td>
                  <span className={`badge badge-${post.assigned_platform}`}>
                    {post.assigned_platform === 'instagram' ? '📸 Instagram' : '▶ YouTube'}
                  </span>
                </td>
                <td><span className={`badge badge-status-${post.post_status}`}>{post.post_status}</span></td>
                <td>
                  {post.generated_media_link && (
                    <a href={`${API_BASE}/generated/images/${post.rss_id}.jpg`} target="_blank" rel="noreferrer">🖼 Image</a>
                  )}
                  {post.published_link && (
                    <> · <a href={post.published_link} target="_blank" rel="noreferrer">🔗 Link</a></>
                  )}
                  {!post.generated_media_link && !post.published_link && <span>-</span>}
                </td>
                <td>
                  <button onClick={() => onGenerateSingle(post.rss_id)} disabled={loading}>Generate</button>
                  <button onClick={() => onRetry(post.rss_id)} disabled={loading}>Retry</button>
                </td>
              </tr>
            ))}
            {!pagedPosts.length && (
              <tr>
                <td colSpan={5}>No posts found for current filters.</td>
              </tr>
            )}
          </tbody>
        </table>
        {totalPages > 1 && (
          <div className="pagination">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>← Prev</button>
            <span>Page {page} of {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>Next →</button>
          </div>
        )}
      </section>
    </div>
  );
}

export default function App() {
  const [currentPage, setCurrentPage] = useState('dashboard'); // 'dashboard' or 'create'

  return (
    <div>
      {/* Page Navigation */}
      <nav className="page-nav">
        <button 
          className={`nav-btn ${currentPage === 'dashboard' ? 'active' : ''}`}
          onClick={() => setCurrentPage('dashboard')}
        >
          📊 Dashboard
        </button>
        <button 
          className={`nav-btn ${currentPage === 'create' ? 'active' : ''}`}
          onClick={() => setCurrentPage('create')}
        >
          ✏️ Content Creator
        </button>
      </nav>

      {currentPage === 'dashboard' ? <Dashboard /> : <Create />}
    </div>
  );
}
