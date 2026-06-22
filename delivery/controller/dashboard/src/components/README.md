# Dashboard Components

Each component in this directory is a single `.jsx` file. All components follow the same conventions for data fetching, styling, and error handling.

---

## Conventions

### Data Fetching

- All API calls target the controller at `http://localhost:8765` (or the current origin in production since the dashboard is served by the controller itself)
- Use relative URLs for API calls (e.g., `/stats`, `/jobs`, `/workers`, `/logs`) so they work in both development (via Vite proxy) and production (served by FastAPI)
- All data-fetching components use `useEffect` with a **5-second polling interval**:

```jsx
// Standard fetch pattern for all components
const [data, setData] = useState(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
  const fetchData = async () => {
    try {
      const res = await fetch('/endpoint');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  fetchData();
  const interval = setInterval(fetchData, 5000);
  return () => clearInterval(interval);
}, []);
```

### Styling

- Use **Tailwind CSS** for all styling — no inline styles, no CSS modules
- Dark theme base: `bg-gray-900` body, `bg-gray-800` cards, `text-white` text
- Cards: `rounded-xl shadow-lg p-6`
- Hover effects: `hover:shadow-xl transition-all duration-300`
- Responsive: Use `grid` with `grid-cols-1 sm:grid-cols-2 lg:grid-cols-4` for cards

### Error & Loading States

Every component must handle three states:

1. **Loading**: Show a pulsing skeleton placeholder (`animate-pulse bg-gray-700 rounded`)
2. **Error**: Show a red-bordered error message with retry affordance
3. **Data**: Show the actual content

### Mobile Responsive

- All components must work on screens from 320px to 1920px wide
- Use Tailwind responsive prefixes: `sm:`, `md:`, `lg:`, `xl:`
- Stack cards vertically on mobile, grid on desktop
- Navigation collapses to hamburger menu on mobile (implemented in `App.jsx`)

---

## Components

### StatsBar.jsx

| Property | Detail |
|----------|--------|
| **API** | `GET /stats` |
| **Refresh** | Every 5 seconds |
| **Props** | None (fetches own data) |

Renders a horizontal row of 4 stat cards:

| Card | Key | Icon | Color |
|------|-----|------|-------|
| Queue Depth | `queue_depth` | 📋 | `bg-blue-500/20 border-blue-500` |
| Done Today | `done_today` | ✅ | `bg-green-500/20 border-green-500` |
| Failed Today | `failed_today` | ❌ | `bg-red-500/20 border-red-500` |
| Active Workers | `active_workers` | 🖥️ | `bg-purple-500/20 border-purple-500` |

Layout: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`

Each card has a colored left border (`border-l-4`), large number value (`text-3xl font-bold`), and label (`text-sm text-gray-400`).

---

### JobCard.jsx

| Property | Detail |
|----------|--------|
| **Props** | `job` object |
| **Refresh** | None (parent manages data) |

Receives a single job object and renders a card showing:

```
┌──────────────────────────────────────────┐
│  ring.3dm                    ● COMPLETED │
│  Worker: DESKTOP-PC01                    │
│  Created: 5 min ago                      │
│  Retries: 0                              │
│                                          │
│  ┌── (only if FAILED) ──────────────┐    │
│  │ Error: TimeoutError: ...         │    │
│  └──────────────────────────────────┘    │
└──────────────────────────────────────────┘
```

Status badge mapping (Tailwind classes):

| Status | Classes |
|--------|---------|
| `PENDING` | `bg-gray-100 text-gray-700` |
| `CLAIMED` | `bg-blue-100 text-blue-700` |
| `PROCESSING` | `bg-yellow-100 text-yellow-700` |
| `COMPLETED` | `bg-green-100 text-green-700` |
| `FAILED` | `bg-red-100 text-red-700` |

The PROCESSING badge should include a subtle animation (`animate-pulse`) to indicate active work.

---

### QueuePage.jsx

| Property | Detail |
|----------|--------|
| **API** | `GET /jobs?status={filter}` |
| **Refresh** | Every 5 seconds |
| **Route** | `/` |

Layout:
1. `StatsBar` at the top
2. Filter buttons bar: All | Pending | Claimed | Processing | Completed | Failed
   - Active filter has `bg-white text-gray-900` styling
   - Inactive filters have `bg-gray-700 text-gray-300` styling
3. List of `JobCard` components below
4. "No jobs found" empty state with illustration

---

### WorkersPage.jsx

| Property | Detail |
|----------|--------|
| **API** | `GET /workers` |
| **Refresh** | Every 5 seconds |
| **Route** | `/workers` |

Layout:
1. `StatsBar` at the top
2. Grid of worker cards

Each worker card shows:

```
┌──────────────────────────────────────┐
│  🟢 DESKTOP-PC01                    │
│                                      │
│  IP:             192.168.1.50        │
│  Last Seen:      3 seconds ago       │
│  Jobs Completed: 42                  │
│  Current Job:    ring.3dm            │
└──────────────────────────────────────┘
```

Status dot colors:
- 🟢 Green: last_seen < 10 seconds ago
- 🟡 Yellow: last_seen 10–30 seconds ago
- (Workers > 30s are not returned by the API)

---

### LogDrawer.jsx

| Property | Detail |
|----------|--------|
| **API** | `GET /logs` |
| **Refresh** | Every 5 seconds |
| **Props** | `isOpen: bool`, `onClose: () => void` |

Slide-in drawer from the right:

```
                              ┌──────────────────────┐
                              │  System Logs      ✕  │
                              │──────────────────────│
                              │ 12:00:00 [INFO]      │
                              │   controller: Started │
                              │ 12:00:01 [INFO]      │
                              │   watcher: Watching   │
                              │ 12:00:05 [INFO]      │
                              │   New file: ring.3dm  │
                              │                      │
                              │                      │
                              │  ▼ (auto-scroll)     │
                              └──────────────────────┘
```

Implementation details:
- Drawer slides in from right using `transform translate-x-full → translate-x-0` with `transition-transform duration-300`
- Background overlay: `bg-black/50` — clicking it calls `onClose()`
- Log container: `overflow-y-auto` with `ref` for auto-scrolling
- Auto-scroll: use `useEffect` to scroll container to bottom when `data.lines` changes
- Font: `font-mono text-xs leading-relaxed`
- Line colors based on log level:
  - Contains `[INFO]` → `text-gray-300`
  - Contains `[WARNING]` → `text-yellow-400`
  - Contains `[ERROR]` → `text-red-400`
  - Contains `[DEBUG]` → `text-gray-500`
- Width: `w-96` on desktop (`lg:`), full width on mobile
