import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine
} from 'recharts'
import { useState, useEffect } from 'react'

const DRIVERS = [
  { key: 'VER', color: '#e8002d' },
  { key: 'LEC', color: '#00e639' },
  { key: 'HAM', color: '#79d1fc' },
]

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload) return null
  return (
    <div style={{
      background: 'var(--s3)', border: '1px solid rgba(255,255,255,0.08)',
      padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 10,
    }}>
      <div style={{ color: 'var(--muted)', marginBottom: 4 }}>LAP {label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color }}>
          {p.dataKey}: {p.value.toFixed(3)}s
        </div>
      ))}
    </div>
  )
}

export default function LapDeltaChart() {
  const [chartData, setChartData] = useState([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch('http://localhost:8000/api/race/telemetry');
        setChartData(await res.json());
      } catch (e) {
        console.error(e);
      }
    };
    fetchData();
    const id = setInterval(fetchData, 3000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="card" style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div>
          <div className="panel-title">Lap Time Delta Trends</div>
          <div className="panel-label" style={{ marginBottom: 0 }}>REAL-TIME TELEMETRY</div>
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          {DRIVERS.map(d => (
            <span key={d.key} style={{ display: 'flex', alignItems: 'center', gap: 6, fontFamily: 'var(--font-mono)', fontSize: 10 }}>
              <span style={{ width: 14, height: 2, background: d.color, display: 'inline-block' }} />
              {d.key}
            </span>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
          <CartesianGrid stroke="rgba(255,255,255,0.05)" strokeDasharray="0" />
          <XAxis
            dataKey="lap" stroke="rgba(255,255,255,0.15)"
            tick={{ fill: 'var(--dim)', fontSize: 9, fontFamily: 'JetBrains Mono' }}
            tickLine={false}
          />
          <YAxis
            stroke="rgba(255,255,255,0.15)"
            tick={{ fill: 'var(--dim)', fontSize: 9, fontFamily: 'JetBrains Mono' }}
            tickLine={false} domain={['auto','auto']}
          />
          <Tooltip content={<CustomTooltip />} />
          {/* Pit window highlight */}
          <ReferenceLine x={45} stroke="rgba(232,0,45,0.4)" strokeDasharray="4 2"
            label={{ value: 'PIT WINDOW', fill: '#e8002d', fontSize: 9, fontFamily: 'JetBrains Mono', position: 'top' }} />
          {DRIVERS.map(d => (
            <Line
              key={d.key} type="monotone" dataKey={d.key}
              stroke={d.color} strokeWidth={2} dot={false}
              activeDot={{ r: 4, fill: d.color, strokeWidth: 0 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
