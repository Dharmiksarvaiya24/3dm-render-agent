import { useState, useEffect } from 'react';

const FILTERS = [
  { label: 'All Jobs', value: '' },
  { label: 'Pending', value: 'PENDING' },
  { label: 'Processing', value: 'PROCESSING' },
  { label: 'Completed', value: 'COMPLETED' },
  { label: 'Failed', value: 'FAILED' },
];

const STATUS_STYLES = {
  PENDING: { color: 'text-gray-400', dot: 'bg-gray-400', pulse: false, label: 'Pending' },
  CLAIMED: { color: 'text-blue-400', dot: 'bg-blue-400', pulse: false, label: 'Claimed' },
  PROCESSING: { color: 'text-primary', dot: 'bg-primary', pulse: true, label: 'Processing' },
  COMPLETED: { color: 'text-tertiary', dot: 'bg-tertiary', pulse: false, label: 'Completed' },
  FAILED: { color: 'text-error', dot: 'bg-error', pulse: false, label: 'Failed' },
};

function parseUtc(dateStr) {
  return new Date((dateStr || '').endsWith('Z') ? dateStr : dateStr + 'Z');
}

function timeAgo(dateStr) {
  const diff = Math.floor((Date.now() - parseUtc(dateStr).getTime()) / 1000);
  if (diff < 60) return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
  return `${Math.floor(diff / 86400)}d`;
}

function QueuePage() {
  const [jobs, setJobs] = useState([]);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchData = async () => {
    try {
      const [jobsRes, statsRes] = await Promise.all([
        fetch(filter ? `/api/jobs?status=${filter}` : '/api/jobs'),
        fetch('/api/stats'),
      ]);
      if (jobsRes.ok) {
        const text = await jobsRes.text();
        try { setJobs(JSON.parse(text)); } catch { console.error('Jobs: invalid JSON'); }
      }
      if (statsRes.ok) {
        const text = await statsRes.text();
        try { setStats(JSON.parse(text)); } catch { console.error('Stats: invalid JSON'); }
      }
    } catch (e) {
      console.error('Fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  const clearAll = async () => {
    try {
      const res = await fetch('/api/jobs', { method: 'DELETE' });
      if (res.ok) {
        setFilter('');
        setJobs([]);
        setStats(null);
        fetchData();
      } else {
        const text = await res.text();
        console.error('Clear failed:', res.status, text);
      }
    } catch (e) {
      console.error('Clear error:', e);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000);
    return () => clearInterval(interval);
  }, [filter]);

  return (
    <div className="animate-fade-in">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-lg mb-2xl">
        <div className="glass-panel p-lg crimson-gradient-border">
          <div className="flex justify-between items-center mb-6">
            <span className="text-[11px] font-bold tracking-[0.2em] text-on-surface-variant uppercase">Pending Jobs</span>
            <span className="material-symbols-outlined text-primary/40">analytics</span>
          </div>
          <div className="flex items-baseline gap-2">
            <h3 className="text-4xl font-light tracking-tight" id="stat-queue-depth">
              {stats ? stats.queue_depth : 0}
            </h3>
          </div>
        </div>
        <div className="glass-panel p-lg crimson-gradient-border">
          <div className="flex justify-between items-center mb-6">
            <span className="text-[11px] font-bold tracking-[0.2em] text-on-surface-variant uppercase">Completed Today</span>
            <span className="material-symbols-outlined text-primary/40">check_circle</span>
          </div>
          <div className="flex items-baseline gap-2">
            <h3 className="text-4xl font-light tracking-tight">
              {stats ? stats.done_today : 0}
            </h3>
          </div>
        </div>
        <div className="glass-panel p-lg crimson-gradient-border">
          <div className="flex justify-between items-center mb-6">
            <span className="text-[11px] font-bold tracking-[0.2em] text-on-surface-variant uppercase">Failed Today</span>
            <span className="material-symbols-outlined text-error/40">dangerous</span>
          </div>
          <div className="flex items-baseline gap-2">
            <h3 className="text-4xl font-light tracking-tight text-error/80">
              {stats ? stats.failed_today : 0}
            </h3>
          </div>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row justify-between items-end sm:items-center gap-lg mb-xl">
        <div className="flex gap-1.5 p-1.5 bg-white/[0.03] border border-white/[0.06] rounded-lg">
          {FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setFilter(f.value)}
              className={`px-5 py-2.5 text-xs font-bold tracking-[0.15em] uppercase rounded-md transition-all duration-200 ${
                filter === f.value
                  ? 'bg-primary text-black shadow-[0_0_12px_rgba(219,106,106,0.3)]'
                  : 'text-on-surface-variant/60 hover:text-white hover:bg-white/5'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-6">
          <div className="flex flex-col items-end">
            <span className="text-[10px] tracking-widest-lg uppercase text-on-surface-variant/40">
              Synchronized
            </span>
            <span className="text-xs font-mono text-primary/80">
              {new Date().toLocaleTimeString([], { hour12: false })}
            </span>
          </div>
          <button
            onClick={fetchData}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-primary/20 hover:border-primary/50 hover:bg-primary/5 transition-all duration-200 group"
            title="Refresh job data"
          >
            <span className="material-symbols-outlined text-primary group-hover:rotate-180 transition-transform duration-700">
              refresh
            </span>
            <span className="text-xs font-bold tracking-widest-lg uppercase text-primary/80 group-hover:text-primary">
              Refresh
            </span>
          </button>
          <button
            onClick={clearAll}
            className="flex items-center gap-2 px-4 py-2 rounded-lg border border-error/30 hover:border-error/60 hover:bg-error/5 transition-all duration-200 group"
            title="Clear all jobs"
          >
            <span className="material-symbols-outlined text-error/70 group-hover:text-error transition-colors">
              delete
            </span>
            <span className="text-xs font-bold tracking-widest-lg uppercase text-error/70 group-hover:text-error transition-colors">
              Clear All
            </span>
          </button>
        </div>
      </div>

      {loading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass-panel p-lg animate-pulse h-24" />
          ))}
        </div>
      )}

      {!loading && jobs.length === 0 && (
        <div className="glass-panel p-2xl text-center border border-dashed border-outline-variant/20">
          <span className="material-symbols-outlined text-6xl text-on-surface-variant/20">inbox</span>
          <p className="text-on-surface-variant/60 text-lg mt-4">No jobs in queue</p>
          <p className="text-on-surface-variant/40 text-sm mt-1 mb-6">
            Drop a .3dm file into the input folder to get started
          </p>
          <button
            onClick={fetchData}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-primary/30 hover:border-primary/60 hover:bg-primary/5 text-primary text-xs font-bold tracking-widest-lg uppercase transition-all duration-200"
          >
            <span className="material-symbols-outlined text-base">refresh</span>
            Check Queue
          </button>
        </div>
      )}

      {!loading && jobs.length > 0 && (
        <div className="space-y-4">
          {jobs.map((job) => {
            const st = STATUS_STYLES[job.status] || STATUS_STYLES.PENDING;
            const borderColor =
              job.status === 'PROCESSING' ? 'border-l-primary' :
              job.status === 'COMPLETED' ? 'border-l-tertiary/40' :
              job.status === 'FAILED' ? 'border-l-error/40' :
              'border-l-gray-500/40';

            return (
              <div
                key={job.id}
                className={`glass-panel p-lg card-hover-effect flex flex-wrap lg:flex-nowrap items-center gap-xl border-l-[3px] ${borderColor}`}
              >
                <div className="flex-1 min-w-[300px]">
                  <div className="flex items-start gap-4">
                    <div className="p-3 bg-primary/5 border border-primary/20">
                      <span className="material-symbols-outlined text-primary">movie</span>
                    </div>
                    <div>
                      <h4 className="text-base font-semibold tracking-wide text-white">
                        {job.file_name}
                      </h4>
                      <p className="text-[11px] font-mono tracking-wider text-on-surface-variant/50 mt-1 uppercase">
                        ID: {job.id.substring(0, 8)}...
                      </p>
                      {job.status === 'FAILED' && job.error_message && (
                        <p className="text-[11px] font-mono text-error/60 mt-2 truncate max-w-md">
                          {job.error_message.substring(0, 120)}
                        </p>
                      )}
                      {job.status === 'COMPLETED' && job.output_path && (
                        <p className="text-[11px] font-mono text-tertiary/60 mt-2 truncate max-w-md">
                          {job.output_path}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
                <div className="w-full lg:w-auto flex items-center justify-between lg:justify-end gap-xl lg:gap-16">
                  <div className="flex flex-col">
                    <span className="text-[9px] font-bold tracking-[0.2em] text-on-surface-variant/40 uppercase mb-1">
                      Status
                    </span>
                    <div className="flex items-center gap-2">
                      <div className={`w-1.5 h-1.5 rounded-full ${st.dot} ${st.pulse ? 'status-pulse' : ''}`}></div>
                      <span className={`text-xs font-bold tracking-widest uppercase ${st.color}`}>
                        {st.label}
                      </span>
                    </div>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[9px] font-bold tracking-[0.2em] text-on-surface-variant/40 uppercase mb-1">
                      Worker
                    </span>
                    <span className="text-xs font-medium tracking-wide">
                      {job.worker_id || 'Unassigned'}
                    </span>
                  </div>
                  <div className="flex flex-col min-w-[80px]">
                    <span className="text-[9px] font-bold tracking-[0.2em] text-on-surface-variant/40 uppercase mb-1">
                      Time
                    </span>
                    <span className="text-xs font-mono">{timeAgo(job.created_at)}</span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default QueuePage;
