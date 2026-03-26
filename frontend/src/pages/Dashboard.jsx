import { RACE_INFO, TIMELINE_EVENTS } from '../data/mockData.js'
import DriverGrid         from '../components/DriverGrid.jsx'
import LapDeltaChart      from '../components/LapDeltaChart.jsx'
import { KpiTile, TelemTile } from '../components/Shared.jsx'

function EventTimeline() {
  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
        <div className="panel-label" style={{ marginBottom: 0 }}>Event Timeline</div>
        <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.05)' }} />
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 9, color: 'var(--green)', display: 'flex', alignItems: 'center', gap: 4 }}>
          <span className="blink">●</span> LIVE
        </span>
      </div>
      <div className="timeline">
        <div className="timeline__line" />
        <div className="timeline__events">
          {TIMELINE_EVENTS.map(ev => (
            <div key={ev.id} className={`t-event${ev.live ? ' t-event--live' : ''}`}>
              <div className="t-event__label" style={{ color: ev.color === 'transparent' ? 'var(--red)' : ev.color }}>
                {ev.label}
              </div>
              {ev.predicted
                ? <div style={{ width: 52, height: 10, border: '1px dashed rgba(232,0,45,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 7, color: 'var(--red)' }}>L45–50</span>
                  </div>
                : <div className="t-event__dot" style={{ background: ev.live ? 'var(--red)' : ev.color }} />
              }
              <div className="t-event__tip">{ev.tip}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default function Dashboard() {
  return (
    <>
      {/* KPI Row */}
      <div className="grid-4">
        <KpiTile label="Optimal Pit Window" value="LAP 45–50" sub="▲ OPEN" subColor="var(--green)" />
        <KpiTile label="Track Temp" value={`${RACE_INFO.trackTemp}°C`} sub="STABLE" subColor="var(--muted)" accent="var(--s3)" />
        <KpiTile label="SC Probability" value={`${(RACE_INFO.scProbability * 100).toFixed(0)}%`} sub="LOW RISK" subColor="var(--muted)" accent="var(--s3)" />
        <KpiTile label="DQN Confidence" value="84.3%" sub="PIT RECOMMENDED" subColor="var(--green)" />
      </div>

      {/* Driver cards + chart */}
      <div className="grid-12">
        <div className="col-5"><DriverGrid /></div>
        <div className="col-7"><LapDeltaChart /></div>
      </div>

      {/* Event timeline */}
      <EventTimeline />

      {/* Dense telemetry row */}
      <div className="grid-4">
        <TelemTile label="Fuel On Board"     value="42.8 KG"  sub="−0.2 TARGET"  subColor="var(--green)" />
        <TelemTile label="ERS Deployment"    value="84%"      sub="NOMINAL"      subColor="var(--muted)" />
        <TelemTile label="Brake Temp (FR)"   value="642°C"    sub="STRESSED"     subColor="var(--red)" />
        <TelemTile label="Last Sector"       value="24.182"   sub="PERSONAL BEST" subColor="var(--green)" />
      </div>
    </>
  )
}
