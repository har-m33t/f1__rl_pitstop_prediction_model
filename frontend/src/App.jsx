import { useState, useEffect } from 'react'
import { RACE_INFO } from './data/mockData.js'
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

function Topbar({ activeTab, setActiveTab, currentLap }) {
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
        <div className="topbar__status">
          <span className="dot-live" />
          {RACE_INFO.event} · LAP {currentLap}/{RACE_INFO.totalLaps}
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: 'var(--dim)' }}>
          {RACE_INFO.weather}
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
  const [currentLap, setCurrentLap] = useState(RACE_INFO.currentLap)

  // Simulate live lap counter
  useEffect(() => {
    const id = setInterval(() => {
      setCurrentLap(l => l < RACE_INFO.totalLaps ? l + 1 : l)
    }, 30000) // advance every 30s
    return () => clearInterval(id)
  }, [])

  return (
    <div className="carbon">
      <Topbar activeTab={activeTab} setActiveTab={setActiveTab} currentLap={currentLap} />
      <Sidenav activeTab={activeTab} setActiveTab={setActiveTab} />
      <main className="main">
        {PAGE_MAP[activeTab]}
      </main>
      <Footer />
    </div>
  )
}
