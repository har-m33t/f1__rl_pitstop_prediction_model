import { useState, useEffect } from 'react'
import DriverGrid         from '../components/DriverGrid.jsx'
import LapDeltaChart      from '../components/LapDeltaChart.jsx'
import { KpiTile, TelemTile } from '../components/Shared.jsx'

function EventTimeline({ selectedRace }) {
  const [events, setEvents] = useState([]);
  useEffect(() => {
    const fetchTimeline = async () => {
      try {
        if (!selectedRace) return;
        const res = await fetch(`http://localhost:8000/api/strategy/timeline?year=${selectedRace.year}&track=${selectedRace.track}`);
        const data = await res.json();
        setEvents(data.events || []);
      } catch (e) {
        console.error(e);
      }
    };
    fetchTimeline();
    const id = setInterval(fetchTimeline, 3000);
    return () => clearInterval(id);
  }, [selectedRace]);

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
          {events.map(ev => (
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

export default function Dashboard({ selectedRace }) {
  const [raceInfo, setRaceInfo] = useState({ scProbability: 0, trackTemp: 0 });
  const [showDqnBreakdown, setShowDqnBreakdown] = useState(false);
  const [dqnObs, setDqnObs] = useState([]);

  useEffect(() => {
    const fetchInfo = async () => {
      try {
        if (!selectedRace) return;
        const res = await fetch(`http://localhost:8000/api/race/info?year=${selectedRace.year}&track=${selectedRace.track}`);
        setRaceInfo(await res.json());

        const obsRes = await fetch(`http://localhost:8000/api/model/observations?year=${selectedRace.year}&track=${selectedRace.track}`);
        setDqnObs(await obsRes.json());
      } catch (e) {
        console.error(e);
      }
    };
    fetchInfo();
    const id = setInterval(fetchInfo, 3000);
    return () => clearInterval(id);
  }, [selectedRace]);

  const getFeature = (searchLabel) => {
    const feature = dqnObs.find(o => o.label.includes(searchLabel));
    return feature || { value: 0, color: 'var(--muted)' };
  };

  const tireAgeFeat = getFeature('tire_age');
  const degFeat = getFeature('degradation');
  const scFeat = getFeature('safety_car');

  return (
    <>
      {/* KPI Row */}
      <div className="grid-4" style={{ position: 'relative' }}>
        <KpiTile label="Optimal Pit Window" value="LAP 45–50" sub="▲ OPEN" subColor="var(--green)" />
        <KpiTile label="Track Temp" value={`${raceInfo.trackTemp}°C`} sub="STABLE" subColor="var(--muted)" accent="var(--s3)" />
        <KpiTile label="SC Probability" value={`${(raceInfo.scProbability * 100).toFixed(0)}%`} sub="LOW RISK" subColor="var(--muted)" accent="var(--s3)" />
        
        <div style={{ position: 'relative' }}>
          <KpiTile 
            label="DQN Confidence" 
            value="84.3%" 
            sub="PIT RECOMMENDED" 
            subColor="var(--green)" 
            onClick={() => setShowDqnBreakdown(!showDqnBreakdown)}
          />

          {showDqnBreakdown && (
            <div className="dqn-panel">
              <div className="panel-title" style={{ marginBottom: 16 }}>Decision Breakdown</div>
              <div className="panel-label">Features Driving Recommendation</div>
              
              <div className="qval-row">
                <div className="qval-row__label">Tire Age Weight</div>
                <div className="qval-row__bar">
                  <div className="qval-row__bar__fill" style={{ width: `${tireAgeFeat.value * 100}%`, background: tireAgeFeat.color }} />
                </div>
                <div className="qval-row__val">{tireAgeFeat.value.toFixed(2)}</div>
              </div>

              <div className="qval-row">
                <div className="qval-row__label">Degradation Slope</div>
                <div className="qval-row__bar">
                  <div className="qval-row__bar__fill" style={{ width: `${degFeat.value * 100}%`, background: degFeat.color }} />
                </div>
                <div className="qval-row__val" style={{ color: degFeat.highlight ? 'var(--red)' : 'white' }}>
                  {degFeat.value.toFixed(2)}{degFeat.highlight ? ' ↑' : ''}
                </div>
              </div>

              <div className="qval-row">
                <div className="qval-row__label">SC Probability</div>
                <div className="qval-row__bar">
                  <div className="qval-row__bar__fill" style={{ width: `${scFeat.value * 100}%`, background: scFeat.color }} />
                </div>
                <div className="qval-row__val">{scFeat.value.toFixed(2)}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Driver cards + chart */}
      <div className="grid-12">
        <div className="col-5"><DriverGrid selectedRace={selectedRace} /></div>
        <div className="col-7"><LapDeltaChart selectedRace={selectedRace} /></div>
      </div>

      {/* Event timeline */}
      <EventTimeline selectedRace={selectedRace} />

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
