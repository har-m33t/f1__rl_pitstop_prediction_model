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

function LoadingOverlay({ visible }) {
  if (!visible) return null;
  return (
    <div style={{
      position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(10, 10, 10, 0.8)', zIndex: 9999, display: 'flex',
      flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      backdropFilter: 'blur(4px)'
    }}>
      <div className="spinner" style={{ width: 40, height: 40, border: '3px solid var(--red)', borderTopColor: 'transparent', borderRadius: '50%', animation: 'spin 1s linear infinite' }} />
      <div style={{ marginTop: 16, fontFamily: 'var(--font-mono)', color: 'var(--dim)', fontSize: 12 }}>
        SYNCING TELEMETRY FROM FASTAPI...
      </div>
      <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

function Topbar({ activeTab, setActiveTab, raceInfo, races, selectedRace, onSelectRace }) {
  if (!raceInfo) return null;
  return (
    <header className="topbar">
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
        {races.length > 0 && selectedRace && (
          <select 
            value={`${selectedRace.year}|${selectedRace.track}`}
            onChange={e => {
              const [y, t] = e.target.value.split('|');
              onSelectRace({ year: parseInt(y), track: t });
            }}
            style={{
              background: 'var(--s1)', color: 'white', border: '1px solid rgba(255,255,255,0.1)',
              padding: '4px 8px', fontFamily: 'var(--font-mono)', fontSize: 11, cursor: 'pointer'
            }}
          >
            {races.map(r => (
              <option key={`${r.year}|${r.track}`} value={`${r.year}|${r.track}`}>
                {r.year} {r.track.toUpperCase()}
              </option>
            ))}
          </select>
        )}
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
        <span style={{ color: 'white' }}>SESSION: HISTORICAL</span>
      </div>
    </footer>
  )
}

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [raceInfo, setRaceInfo] = useState({ event: 'LOADING...', totalLaps: 0, currentLap: 0, weather: '', trackTemp: 0, scProbability: 0 })
  const [races, setRaces] = useState([])
  const [selectedRace, setSelectedRace] = useState(null)
  const [isLoading, setIsLoading] = useState(true)

  // Fetch Race List once
  useEffect(() => {
    fetch('http://localhost:8000/api/race/list')
      .then(r => r.json())
      .then(data => {
        setRaces(data);
        if (data.length > 0) setSelectedRace(data[0]);
      })
      .catch(console.error);
  }, []);

  // Fetch Race info and toggle loading when selectedRace changes
  useEffect(() => {
    if (!selectedRace) return;
    
    setIsLoading(true);
    const fetchData = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/race/info?year=${selectedRace.year}&track=${selectedRace.track}`);
        const data = await res.json();
        setRaceInfo(data);
        
        // Artificial delay so the loading screen is visible (and gives child components time to fetch simultaneously)
        setTimeout(() => setIsLoading(false), 800);
      } catch (e) {
        console.error("Failed to fetch race info", e);
        setIsLoading(false);
      }
    };
    fetchData();
    
    const id = setInterval(fetchData, 3000);
    return () => clearInterval(id);
  }, [selectedRace]);

  const PAGE_MAP = {
    dashboard: <Dashboard selectedRace={selectedRace} />,
    strategy:  <Strategy selectedRace={selectedRace} />,
    tyres:     <Tyres selectedRace={selectedRace} />,
    model:     <RlModel selectedRace={selectedRace} />,
  }

  return (
    <div className="carbon">
      <Topbar activeTab={activeTab} setActiveTab={setActiveTab} raceInfo={raceInfo} races={races} selectedRace={selectedRace} onSelectRace={setSelectedRace} />
      <Sidenav activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="main" style={{ position: 'relative' }}>
        <LoadingOverlay visible={isLoading} />
        {PAGE_MAP[activeTab]}
      </main>
      <Footer />
    </div>
  )
}
