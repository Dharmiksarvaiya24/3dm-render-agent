const STATUS_CONFIG = {
  PENDING: { bg: 'bg-gray-100', text: 'text-gray-700', label: 'PENDING' },
  CLAIMED: { bg: 'bg-blue-100', text: 'text-blue-700', label: 'CLAIMED' },
  PROCESSING: { bg: 'bg-yellow-100', text: 'text-yellow-700', label: 'PROCESSING', animate: true },
  COMPLETED: { bg: 'bg-green-100', text: 'text-green-700', label: 'COMPLETED' },
  FAILED: { bg: 'bg-red-100', text: 'text-red-700', label: 'FAILED' },
};

function timeAgo(dateStr) {
  const now = Date.now();
  const then = new Date(dateStr).getTime();
  const diff = Math.floor((now - then) / 1000);

  if (diff < 60) return `${diff}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function JobCard({ job }) {
  const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.PENDING;

  return (
    <div className="bg-gray-800 rounded-xl shadow-lg p-5 hover:shadow-xl transition-all duration-300 border border-gray-700">
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-lg font-bold text-white truncate max-w-[70%]">
          {job.file_name}
        </h3>
        <span
          className={`px-3 py-1 rounded-full text-xs font-semibold ${cfg.bg} ${cfg.text} ${
            cfg.animate ? 'animate-pulse' : ''
          }`}
        >
          {cfg.label}
        </span>
      </div>

      <div className="space-y-1.5 text-sm text-gray-400">
        <p>
          <span className="text-gray-500">Worker:</span>{' '}
          {job.worker_id || 'Unassigned'}
        </p>
        <p>
          <span className="text-gray-500">Created:</span>{' '}
          {timeAgo(job.created_at)}
        </p>
        {job.retry_count > 0 && (
          <p>
            <span className="text-gray-500">Retries:</span>{' '}
            {job.retry_count}
          </p>
        )}

        {job.status === 'FAILED' && job.error_message && (
          <div className="mt-3 p-3 bg-red-900/20 border border-red-500/30 rounded-lg">
            <p className="text-xs text-red-400 font-mono break-all">
              {job.error_message.substring(0, 300)}
              {job.error_message.length > 300 ? '...' : ''}
            </p>
          </div>
        )}

        {job.status === 'COMPLETED' && job.output_path && (
          <p className="mt-2 text-xs text-green-400 font-mono truncate">
            {job.output_path}
          </p>
        )}
      </div>
    </div>
  );
}

export default JobCard;