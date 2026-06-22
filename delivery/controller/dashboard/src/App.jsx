import { Routes, Route, NavLink } from 'react-router-dom';
import QueuePage from './components/QueuePage';
import WorkersPage from './components/WorkersPage';


const linkClass = ({ isActive }) =>
  `text-base font-bold tracking-widest-lg uppercase transition-all duration-300 ${
    isActive
      ? 'text-primary border-b-2 border-primary pb-1'
      : 'text-on-surface-variant/70 hover:text-primary hover:border-b-2 hover:border-primary/40 pb-1'
  }`;

function App() {
  return (
    <div className="flex flex-col h-screen overflow-hidden bg-black">
      <header className="flex justify-between items-center w-full px-margin h-24 glass-nav sticky top-0 z-50">
        <div className="flex items-center gap-xl">
          <div className="flex items-center gap-lg">
            <img
              alt="Trident_Agent Logo"
              className="h-16 w-auto brightness-110 drop-shadow-[0_0_12px_rgba(219,106,106,0.3)]"
              src="https://lh3.googleusercontent.com/aida-public/AB6AXuDjijhuX8W4Fmt-DzMJhef5Fk_Oe0pArV-IwxrvkWx_Y4ppwmphOPl1s2GIJRbj8yFHrKYL9joKlXcSPHds2MICQ6jVyjYyl09oYIBowlFlfxpnwV20hu9glXcFTgwA7MA23LOZcqPCsu5eys-fQO_2NSLlP0oOejrQnxa5QAmnmnSnyRCPEN51aANp4jtdXCBW2FlGVW9jXTVL26K7z-l8qlIdLhG4NnX4omJiRfeprpmuKCRGTiae2yW4zhzOjOZU-dRRoRFFSJY"
            />
            <div className="flex flex-col ml-3">
              <span className="text-2xl font-bold text-primary uppercase tracking-widest-lg leading-none">
                Trident Agent
              </span>
              <span className="text-[11px] text-on-surface-variant/60 font-medium tracking-[0.2em] mt-1 uppercase">
                JEWELLERY RENDER SYSTEM v1.0.0
              </span>
            </div>
          </div>
        </div>
        <nav className="hidden md:flex items-center gap-12">
          <NavLink to="/" end className={linkClass}>QUEUE</NavLink>
          <NavLink to="/workers" className={linkClass}>WORKERS</NavLink>
        </nav>
      </header>
      <main className="flex-1 overflow-y-auto bg-[radial-gradient(circle_at_top_right,_rgba(219,106,106,0.05)_0%,_transparent_50%)]">
        <div className="p-xl max-w-[1400px] mx-auto w-full animate-fade-in">
          <Routes>
            <Route path="/" element={<QueuePage />} />
            <Route path="/workers" element={<WorkersPage />} />
          </Routes>
        </div>
      </main>
    </div>
  );
}

export default App;
