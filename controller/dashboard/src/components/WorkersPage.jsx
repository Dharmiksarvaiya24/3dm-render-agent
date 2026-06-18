import { useState, useEffect } from 'react';

function parseUtc(dateStr) {
  return new Date((dateStr || '').endsWith('Z') ? dateStr : dateStr + 'Z');
}

function timeSince(dateStr) {
  const seconds = Math.floor((Date.now() - parseUtc(dateStr).getTime()) / 1000);
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  return 'Offline';
}

function WorkersPage() {
  const [workers, setWorkers] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchWorkers = async () => {
    try {
      const res = await fetch('/api/workers');
      if (res.ok) {
        const text = await res.text();
        try { setWorkers(JSON.parse(text)); } catch { console.error('Workers: invalid JSON'); }
      }
    } catch (e) {
      console.error('Fetch workers error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkers();
    const interval = setInterval(fetchWorkers, 5000);
    return () => clearInterval(interval);
  }, []);

  const activeCount = workers.filter((w) => {
    const secondsAgo = Math.floor((Date.now() - parseUtc(w.last_seen).getTime()) / 1000);
    return secondsAgo < 30;
  }).length;

  return (
    <div className="animate-fade-in">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between mb-xl gap-md">
        <div>
          <h1 className="text-4xl font-light text-on-surface mb-2 tracking-tight">
            Compute <span className="font-bold text-primary">Fleet</span>
          </h1>
          <p className="text-sm font-medium text-outline/80 tracking-wide uppercase">
            Overview of all connected worker machines
          </p>
        </div>
        <div>
          <button
            onClick={fetchWorkers}
            className="glass-panel px-lg py-md flex items-center gap-lg min-w-[220px] hover:bg-white/[0.02] transition-all duration-200 cursor-pointer"
            title="Refresh worker list"
          >
          <div className="flex flex-col">
            <span className="text-[10px] text-outline/60 font-bold uppercase tracking-widest-plus mb-1">
              Active Computers
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold text-on-surface">{activeCount}</span>
              <span className="text-xs font-bold text-tertiary">ONLINE</span>
            </div>
          </div>
          <div className="ml-auto w-10 h-10 rounded-full border-2 border-tertiary/20 flex items-center justify-center relative group-hover:border-tertiary/40 transition-colors">
            <div className="absolute inset-0 border-t-2 border-tertiary rounded-full rotate-45"></div>
            <span className="material-symbols-outlined text-tertiary text-lg">memory</span>
          </div>
        </button>
      </div>
      </div>

      {loading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8">
          {[1, 2, 3].map((i) => (
            <div key={i} className="glass-panel p-xl min-h-[220px] animate-pulse" />
          ))}
        </div>
      )}

      {!loading && workers.length === 0 && (
        <div className="glass-panel p-2xl text-center border border-dashed border-outline-variant/20">
          <span className="material-symbols-outlined text-6xl text-on-surface-variant/20">dns</span>
          <p className="text-on-surface-variant/60 text-lg mt-4">No workers detected</p>
          <p className="text-on-surface-variant/40 text-sm mt-1 mb-6">
            Start a worker on another machine to see it here
          </p>
          <button
            onClick={fetchWorkers}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg border border-primary/30 hover:border-primary/60 hover:bg-primary/5 text-primary text-xs font-bold tracking-widest-lg uppercase transition-all duration-200"
          >
            <span className="material-symbols-outlined text-base">refresh</span>
            Scan for Workers
          </button>
        </div>
      )}

      {!loading && workers.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-8" id="worker-grid">
          {workers.map((w) => {
            const secondsAgo = Math.floor((Date.now() - parseUtc(w.last_seen).getTime()) / 1000);
            const isOnline = secondsAgo < 30;
            const util = w.utilization != null ? w.utilization : (isOnline ? 50 : 0);
            const temp = w.temperature != null ? w.temperature : (isOnline ? 45 : '--');
            const fans = w.fan_speed != null ? w.fan_speed : (isOnline ? 60 : '--');

            return (
              <div
                key={w.worker_id}
                className={`glass-panel p-xl flex flex-col justify-between min-h-[220px] card-hover-effect ${!isOnline ? 'opacity-70' : ''}`}
              >
                <div className="flex justify-between items-start mb-6">
                  <div className="flex flex-col">
                    <h3 className="text-on-surface font-bold text-lg mb-1 tracking-tight">
                      {w.worker_id}
                    </h3>
                    <span className="text-outline/60 text-[11px] font-mono tracking-widest uppercase">
                      {w.ip}
                    </span>
                  </div>
                  <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
                    isOnline ? 'bg-surface-container border border-outline-variant/30' : 'bg-error/10 border border-error/30'
                  }`}>
                    <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-tertiary pulse-glow' : 'bg-error'}`}></div>
                    <span className={`text-[10px] font-black tracking-widest ${isOnline ? 'text-tertiary' : 'text-error'}`}>
                      {isOnline ? 'ACTIVE' : 'TIMEOUT'}
                    </span>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4 mb-6">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-outline/50 uppercase font-bold tracking-widest mb-2">Util</span>
                    <div className="h-1 w-full bg-surface-container rounded-full overflow-hidden">
                      <div className="h-full bg-primary shadow-[0_0_8px_rgba(219,106,106,0.3)]" style={{ width: `${util}%` }}></div>
                    </div>
                  </div>
                  <div className="flex flex-col">
                    <span className="text-[10px] text-outline/50 uppercase font-bold tracking-widest mb-2">Temp</span>
                    <span className="text-sm font-bold text-on-surface">{temp}{isOnline ? '°C' : ''}</span>
                  </div>
                  <div className="flex flex-col text-right">
                    <span className="text-[10px] text-outline/50 uppercase font-bold tracking-widest mb-2">Fans</span>
                    <span className="text-sm font-bold text-on-surface">{fans}{isOnline ? '%' : ''}</span>
                  </div>
                </div>

                <div className="flex justify-between items-end pt-4 border-t border-outline-variant/20">
                  <div className="flex flex-col">
                    <span className="text-[10px] text-outline/50 uppercase font-bold tracking-widest">Throughput</span>
                    <span className="text-lg font-bold text-on-surface">
                      {w.jobs_completed} <span className="text-[10px] text-outline font-normal">JOBS</span>
                    </span>
                  </div>
                  <div className="flex flex-col text-right">
                    <span className="text-[10px] text-outline/50 uppercase font-bold tracking-widest">Heartbeat</span>
                    <span className="text-sm font-mono text-outline font-medium tracking-tight">{timeSince(w.last_seen)}</span>
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

export default WorkersPage;
