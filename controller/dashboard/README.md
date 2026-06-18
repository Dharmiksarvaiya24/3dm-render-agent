# Controller Dashboard — React SPA

A React single-page application built with **Vite** and **Tailwind CSS** that provides a real-time monitoring dashboard for the RenderAgent system. It displays queue status, job details, worker health, and system logs.

---

## Tech Stack

| Tool | Version | Purpose |
|------|---------|---------|
| React | ^18 | UI framework |
| React Router DOM | ^6 | Client-side routing (Queue and Workers pages) |
| Vite | ^5 | Build tool and dev server |
| Tailwind CSS | ^3 | Utility-first CSS styling |
| PostCSS | ^8 | CSS processing (required by Tailwind) |
| Autoprefixer | ^10 | Vendor prefix automation |

---

## Build & Deploy

### Development

```bash
cd controller/dashboard
npm install
npm run dev
# Opens at http://localhost:5173 with hot reload
# API calls proxy to http://localhost:8765
```

### Production Build

```bash
cd controller/dashboard
npm install
npm run build
# Output → dist/ folder
```

The `dist/` folder is served by the FastAPI controller as static files at the root path `/`. When a user visits `http://<controller-ip>:8765/`, they see this dashboard.

### Vite Config Notes

Configure `vite.config.js` with a proxy for development:

```
// vite.config.js should include:
server: {
  proxy: {
    '/jobs': 'http://localhost:8765',
    '/workers': 'http://localhost:8765',
    '/stats': 'http://localhost:8765',
    '/logs': 'http://localhost:8765',
  }
}
```

---

## Auto-Refresh

All data-fetching components use `useEffect` with a **5-second polling interval** to keep the dashboard in sync with the controller:

```
// Pattern used in every data-fetching component:
useEffect(() => {
  const fetchData = async () => { /* fetch from API */ };
  fetchData();
  const interval = setInterval(fetchData, 5000);
  return () => clearInterval(interval);
}, []);
```

---

## Pages & Components

### App.jsx — Application Root

- Sets up React Router with two routes:
  - `/` → `QueuePage`
  - `/workers` → `WorkersPage`
- Top navigation bar with links to both pages
- Navigation bar includes:
  - RenderAgent logo/title (left)
  - Queue link (left)
  - Workers link (left)
  - Log button (right) — toggles `LogDrawer`
- Navigation highlights the active page

---

### QueuePage.jsx — Job Queue View

- **Top section**: `StatsBar` component showing 4 stat cards
- **Filter bar**: Buttons to filter jobs by status (All, Pending, Claimed, Processing, Completed, Failed)
- **Job list**: Vertical list of `JobCard` components
- Fetches from `GET /jobs?status={filter}` every 5 seconds
- Shows "No jobs yet" message when queue is empty
- Jobs sorted by most recent first

---

### WorkersPage.jsx — Active Workers View

- **Top section**: `StatsBar` component (same as queue page)
- **Worker list**: Cards showing each active worker
- Fetches from `GET /workers` every 5 seconds
- Each worker card displays:
  - `worker_id` (e.g., `DESKTOP-PC01`)
  - `ip` address
  - `last_seen` relative time (e.g., "3 seconds ago")
  - `jobs_completed` count
  - `current_job_id` (or "Idle" if null)
  - Status indicator: green dot if last_seen < 10s, yellow if < 30s
- Shows "No active workers" message when none connected

---

### StatsBar.jsx — Statistics Cards

- Fetches from `GET /stats` every 5 seconds
- Displays 4 cards in a horizontal row (responsive grid):

| Card | Value Source | Icon/Color |
|------|-------------|------------|
| Queue Depth | `stats.queue_depth` | 📋 Blue background |
| Done Today | `stats.done_today` | ✅ Green background |
| Failed Today | `stats.failed_today` | ❌ Red background |
| Active Workers | `stats.active_workers` | 🖥️ Purple background |

- Each card shows the label, large number value, and an icon
- Cards use `rounded-xl shadow-lg` with colored left border

---

### JobCard.jsx — Single Job Display

- Receives a job object as props
- Displays:
  - **File name** (large, bold)
  - **Status badge** (colored pill — see colors below)
  - **Worker ID** that processed it (or "Unassigned")
  - **Created time** as relative time (e.g., "5 min ago")
  - **Error message** (only shown if status is FAILED, in a red-tinted box)
  - **Output path** (only shown if status is COMPLETED)
  - **Retry count** (only shown if > 0)

#### Status Badge Colors

| Status | Background | Text | Tailwind Classes |
|--------|-----------|------|-----------------|
| `PENDING` | Gray | Dark gray | `bg-gray-100 text-gray-700` |
| `CLAIMED` | Blue | Dark blue | `bg-blue-100 text-blue-700` |
| `PROCESSING` | Yellow | Dark yellow | `bg-yellow-100 text-yellow-700` |
| `COMPLETED` | Green | Dark green | `bg-green-100 text-green-700` |
| `FAILED` | Red | Dark red | `bg-red-100 text-red-700` |

---

### LogDrawer.jsx — Slide-In Log Viewer

- Slide-in drawer from the right side of the screen
- Toggled by a button in the navigation bar
- Fetches from `GET /logs` every 5 seconds
- Displays log lines in a monospace font (`font-mono text-sm`)
- Auto-scrolls to the bottom when new logs appear
- Has a close button (X) in the top-right corner
- Background overlay (semi-transparent) when open — click to close
- Drawer width: `w-96` on desktop, full width on mobile
- Each log line is color-coded:
  - `[INFO]` → default text color
  - `[WARNING]` → yellow text
  - `[ERROR]` → red text
  - `[DEBUG]` → gray text

---

## Styling Guidelines

- Use Tailwind CSS for ALL styling — no custom CSS files (except Tailwind base imports in `index.css`)
- Dark theme: `bg-gray-900` body, `bg-gray-800` cards, `text-white` primary text
- Border radius: `rounded-xl` for cards, `rounded-full` for badges
- Shadows: `shadow-lg` for cards
- Transitions: `transition-all duration-300` for hover effects and drawer
- Responsive: Mobile-first with `sm:`, `md:`, `lg:` breakpoints
- Font: Use system font stack via Tailwind's default `font-sans`

---

## File Structure

```
dashboard/
├── index.html              # SPA entry HTML — mounts React at #root
├── package.json            # Dependencies and scripts
├── vite.config.js          # Vite config with API proxy
├── tailwind.config.js      # Tailwind config — content paths
├── postcss.config.js       # PostCSS config — tailwind + autoprefixer
├── dist/                   # (Generated) Production build
└── src/
    ├── main.jsx            # ReactDOM.createRoot() entry
    ├── App.jsx             # Router + navigation layout
    ├── index.css           # @tailwind base/components/utilities
    └── components/
        ├── README.md       # Component documentation
        ├── StatsBar.jsx    # 4-card statistics display
        ├── JobCard.jsx     # Single job card with status badge
        ├── QueuePage.jsx   # Queue page — stats + job list + filters
        ├── WorkersPage.jsx # Workers page — active worker list
        └── LogDrawer.jsx   # Slide-in log viewer drawer
```
