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
        PULLING RACE TELEMETRY AND UPDATING UI...
      </div>
      <style>{`@keyframes spin { 100% { transform: rotate(360deg); } }`}</style>
    </div>
  )
}

function Topbar({ activeTab, setActiveTab, raceInfo, metadata, selectedRace, onSelectRace }) {
  if (!raceInfo || !metadata) return null;
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
      <div className="topbar__right" style={{ gap: 12 }}>
        {metadata.tracks && (
          <div style={{ display: 'flex', gap: 8 }}>
            <select 
              value={selectedRace?.track || ''}
              onChange={e => onSelectRace({ track: e.target.value, year: selectedRace?.year || metadata.years[0] })}
              style={{
                background: 'var(--s1)', color: 'white', border: '1px solid rgba(255,255,255,0.1)',
                padding: '4px 8px', fontFamily: 'var(--font-mono)', fontSize: 11, cursor: 'pointer'
              }}
            >
              <option value="" disabled>Select Track</option>
              {metadata.tracks.map(t => <option key={t} value={t}>{t.toUpperCase()}</option>)}
            </select>
            
            {selectedRace?.track && (
              <select 
                value={selectedRace?.year || ''}
                onChange={e => onSelectRace({ ...selectedRace, year: parseInt(e.target.value) })}
                style={{
                  background: 'var(--s1)', color: 'white', border: '1px solid rgba(255,255,255,0.1)',
                  padding: '4px 8px', fontFamily: 'var(--font-mono)', fontSize: 11, cursor: 'pointer'
                }}
              >
                <option value="" disabled>Select Year</option>
                {metadata.years.map(y => <option key={y} value={y}>{y}</option>)}
              </select>
            )}
          </div>
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
  const [metadata, setMetadata] = useState({ tracks: [], years: [] })
  const [selectedRace, setSelectedRace] = useState(null)
  const [isLoading, setIsLoading] = useState(false)

  // Fetch Metadata once
  useEffect(() => {
    fetch('http://localhost:8000/api/metadata')
      .then(r => r.json())
      .then(data => {
        setMetadata(data);
        if (data.tracks.length > 0 && data.years.length > 0) {
          // Setup a default initial race selection
          setSelectedRace({ track: 'Monaco', year: 2024 });
        }
      })
      .catch(console.error);
  }, []);

  // Fetch Race info and toggle loading when selectedRace changes
  useEffect(() => {
    if (!selectedRace || !selectedRace.track || !selectedRace.year) return;
    
    setIsLoading(true);
    const fetchData = async () => {
      try {
        const res = await fetch(`http://localhost:8000/api/race/info?year=${selectedRace.year}&track=${selectedRace.track}`);
        if (!res.ok) throw new Error('API Error');
        const data = await res.json();
        setRaceInfo(data);
        
        // Artificial delay so the loading screen feels substantial while backend processes
        setTimeout(() => setIsLoading(false), 1500);
      } catch (e) {
        console.error("Failed to fetch race info", e);
        setTimeout(() => setIsLoading(false), 1500);
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
      <Topbar activeTab={activeTab} setActiveTab={setActiveTab} raceInfo={raceInfo} metadata={metadata} selectedRace={selectedRace} onSelectRace={setSelectedRace} />
      <Sidenav activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="main" style={{ position: 'relative' }}>
        <LoadingOverlay visible={isLoading} />
        {PAGE_MAP[activeTab]}
      </main>
      <Footer />
    </div>
  )
}
