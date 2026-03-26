import { useState, useEffect } from 'react'
import { DRIVERS } from '../data/mockData.js'

const COMPOUND_COLORS = { SOFT: '#e8002d', MEDIUM: '#eab308', HARD: '#ffffff', INTER: '#79d1fc' }

function DriverCard({ driver }) {
  const [integrity, setIntegrity] = useState(driver.tyreIntegrity)

  useEffect(() => {
    const id = setInterval(() => {
      setIntegrity(v => Math.max(15, v - Math.random() * 0.15))
    }, 2500)
    return () => clearInterval(id)
  }, [])

  const dotColor = COMPOUND_COLORS[driver.compound] || '#888'
  const barColor = integrity > 50 ? '#e8002d' : integrity > 30 ? '#eab308' : '#e8002d'

  return (
    <div className="card driver-card" style={{ paddingLeft: 20 }}>
      <div className="driver-card__accent" style={{ background: driver.teamColor }} />
      <div className="driver-card__pos">P{driver.position} · LAP 42</div>
      <div className="driver-card__name">{driver.name}</div>
      <div className="driver-card__compound">
        <span className="compound-dot" style={{ background: dotColor }} />
        <span>{driver.compound} · {driver.tyreAge}L</span>
      </div>
      <div className="tyre-bar">
        <div
          className="tyre-bar__fill"
          style={{ width: `${integrity}%`, background: barColor }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 4 }}>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--dim)' }}>
          TYRE INTEGRITY
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: barColor }}>
          {integrity.toFixed(0)}%
        </span>
      </div>
      <div className="driver-card__gap" style={{ color: driver.position === 1 ? 'var(--green)' : 'var(--red)' }}>
        {driver.gap}
      </div>

      {/* DQN hover overlay */}
      <div className="driver-card__overlay">
        <div className="dqn-badge">DQN RECOMMENDATION</div>
        <div className="dqn-rec">{driver.dqnRec}</div>
        <div className="dqn-sub">EST. DELTA {driver.dqnDelta}</div>
      </div>
    </div>
  )
}

export default function DriverGrid() {
  return (
    <div className="grid-2">
      {DRIVERS.map(d => <DriverCard key={d.code} driver={d} />)}
    </div>
  )
}
