import { useState, useEffect } from 'react'
import { Icon } from './components/Shared.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Strategy  from './pages/Strategy.jsx'
import Tyres     from './pages/Tyres.jsx'
import RlModel   from './pages/RlModel.jsx'

const TABS = [
  { id: 'dashboard', icon: 'dashboard',       label: 'DASHBOARD' },
  { id: 'strategy',  icon: 'route',           label: 'STRATEGY'  },
  { id: 'tyres',     icon: 'tire_repair',     label: 'TYRES'     },
  { id: 'model',     icon: 'model_training',  label: 'RL MODEL'  },
]

function Topbar({ activeTab, setActiveTab, raceInfo }) {
  if (!raceInfo) return null;
  return (
    <header className="topbar !static !w-full !flex-shrink-0 z-40 border-b border-white/5">
      <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
        <span className="topbar__logo">STRAT-OS</span>
        <nav className="topbar__nav">
          {TABS.map(t => (
            <a
              key={t.id}
              href={`#${t.id}`}
              className={activeTab === t.id ? 'active' : ''}
              onClick={e => { e.preventDefault(); setActiveTab(t.id) }}
            >
              {t.label}
            </a>
          ))}
        </nav>
      </div>
      <div className="topbar__right">
        <div className="topbar__status">
          <span className="dot-live" />
          {raceInfo.event} · LAP {raceInfo.currentLap}/{raceInfo.totalLaps}
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--dim)' }}>
          {raceInfo.weather}
        </div>
        <Icon name="notifications" style={{ color: 'var(--dim)', cursor: 'pointer', fontSize: 20 }} />
        <Icon name="account_circle" style={{ color: 'var(--dim)', cursor: 'pointer', fontSize: 20 }} />
      </div>
    </header>
  )
}

// Sidenav component is no longer used, but keeping it for context if not explicitly removed
function Sidenav({ activeTab, setActiveTab }) {
  return (
    <nav className="sidenav">
      {TABS.map(t => (
        <button
          key={t.id}
          className={`sidenav__btn${activeTab === t.id ? ' active' : ''}`}
          onClick={() => setActiveTab(t.id)}
          title={t.label}
        >
          <Icon name={t.icon} />
          <span className="sidenav__tip">{t.label}</span>
        </button>
      ))}
      <div className="sidenav__spacer" />
      <button className="sidenav__btn" title="SETTINGS">
        <Icon name="settings" />
        <span className="sidenav__tip">SETTINGS</span>
      </button>
    </nav>
  )
}

function Footer() {
  return (
    <footer className="footer">
      <div className="footer__left">
        <span style={{ color: 'var(--red)', fontWeight: 700 }}>LIVE STATUS: NOMINAL</span>
        <span style={{ color: 'var(--dim)' }}>TELEMETRY: CONNECTED</span>
        <span style={{ color: 'var(--dim)' }}>MODEL: DQN v2.7.1</span>
      </div>
      <div className="footer__right">
        <span>LATENCY: 14MS</span>
        <span style={{ color: 'white' }}>SESSION: LIVE</span>
      </div>
    </footer>
  )
}

const PAGE_MAP = {
  dashboard: <Dashboard />,
  strategy:  <Strategy />,
  tyres:     <Tyres />,
  model:     <RlModel />,
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [raceInfo, setRaceInfo] = useState({ event: 'LOADING...', totalLaps: 0, currentLap: 0, weather: '', trackTemp: 0, scProbability: 0 })

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/race/info');
        const data = await res.json();
        setRaceInfo(data);
      } catch (e) {
        console.error("Failed to fetch race info", e);
      }
    };
    fetchData();
    const id = setInterval(fetchData, 2000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="carbon flex h-screen w-screen overflow-hidden">
      <div className="flex-none h-full z-50">
        <TwoLevelSidebar activeTab={activeTab} setActiveTab={setActiveTab} />
      </div>
      <div className="flex-1 flex flex-col h-full overflow-hidden relative">
        <Topbar activeTab={activeTab} setActiveTab={setActiveTab} raceInfo={raceInfo} />
        <main className="main !m-0 !w-full flex-1 overflow-y-auto min-h-0 relative">
          {PAGE_MAP[activeTab]}
        </main>
        <Footer />
      </div>
    </div>
  )
}
