// Mock data for the F1 Pit Stop dashboard (will be replaced by FastAPI calls)

export const RACE_INFO = {
  event: 'MONACO GP',
  totalLaps: 78,
  currentLap: 42,
  weather: 'SUNNY 24°C',
  trackTemp: 48.2,
  scProbability: 0.12,
};

export const DRIVERS = [
  {
    code: 'VER', name: 'VERSTAPPEN', position: 1,
    teamColor: '#3671C6', compound: 'SOFT', tyreAge: 18,
    tyreIntegrity: 64, gap: '+12.482s', interval: 'LEADER',
    dqnRec: 'BOX LAP 47', dqnDelta: '−2.1s', lapTime: '1:13.842',
    lapTimes: [80,79,78,77,76,78,79,80,81,82,83],
  },
  {
    code: 'LEC', name: 'LECLERC', position: 2,
    teamColor: '#F91536', compound: 'MEDIUM', tyreAge: 12,
    tyreIntegrity: 42, gap: '−0.842s', interval: '+12.482s',
    dqnRec: 'BOX NOW', dqnDelta: 'TYRES CRITICAL', lapTime: '1:14.221',
    lapTimes: [82,81,82,83,84,85,86,87,87,88,89],
  },
  {
    code: 'HAM', name: 'HAMILTON', position: 3,
    teamColor: '#27F4D2', compound: 'HARD', tyreAge: 21,
    tyreIntegrity: 71, gap: '+4.104s', interval: '+16.586s',
    dqnRec: 'STAY OUT', dqnDelta: 'ΔQ=−0.31', lapTime: '1:15.102',
    lapTimes: [85,85,84,84,85,85,86,86,86,87,87],
  },
  {
    code: 'NOR', name: 'NORRIS', position: 4,
    teamColor: '#FF8000', compound: 'SOFT', tyreAge: 8,
    tyreIntegrity: 88, gap: '+8.551s', interval: '+20.033s',
    dqnRec: 'STAY OUT', dqnDelta: 'TYRES FRESH', lapTime: '1:14.581',
    lapTimes: [79,79,78,78,79,79,80,80,80,81,81],
  },
];

export const LAP_CHART_DATA = Array.from({ length: 23 }, (_, i) => ({
  lap: 20 + i,
  VER: 73.5 + Math.sin(i * 0.4) * 0.8 + i * 0.06,
  LEC: 74.2 + Math.sin(i * 0.3 + 1) * 0.7 + i * 0.09,
  HAM: 75.1 + Math.sin(i * 0.2 + 2) * 0.5 + i * 0.04,
}));

export const TIMELINE_EVENTS = [
  { id: 'sc1',  label: 'SC',  color: '#eab308', tip: 'SAFETY CAR L12–L15' },
  { id: 'pit1', label: 'PIT', color: '#e8002d', tip: 'VER PIT L28 (2.4s)' },
  { id: 'vsc',  label: 'VSC', color: '#a16207', tip: 'VSC L35' },
  { id: 'live', label: 'NOW', color: '#e8002d', live: true, tip: 'L42 LIVE' },
  { id: 'win',  label: 'EST', color: 'transparent', predicted: true, tip: 'PIT WINDOW L45–50' },
];

export const STINTS = [
  { driver: 'VER', segs: [{ pct: 30, color: 'rgba(232,0,45,0.35)' }, { pct: 40, color: 'rgba(234,179,8,0.35)' }, { pct: 30, color: 'rgba(255,255,255,0.15)' }], pits: [30, 70], predicted: [68] },
  { driver: 'HAM', segs: [{ pct: 42, color: 'rgba(234,179,8,0.35)' }, { pct: 58, color: 'rgba(255,255,255,0.15)' }], pits: [42], predicted: [40] },
  { driver: 'LEC', segs: [{ pct: 28, color: 'rgba(232,0,45,0.35)' }, { pct: 42, color: 'rgba(234,179,8,0.35)' }, { pct: 30, color: 'rgba(255,255,255,0.15)' }], pits: [28, 70], predicted: [72] },
  { driver: 'NOR', segs: [{ pct: 55, color: 'rgba(232,0,45,0.35)' }, { pct: 45, color: 'rgba(255,255,255,0.15)' }], pits: [55], predicted: [60] },
];

export const TYRE_COMPOUNDS = [
  { name: 'SOFT',   color: '#e8002d', life: '~25L', deg: 'HIGH',     points: 'M0,5 Q20,6 40,15 T70,40 T100,58' },
  { name: 'MEDIUM', color: '#eab308', life: '~35L', deg: 'MEDIUM',   points: 'M0,5 Q30,7 60,22 T100,50' },
  { name: 'HARD',   color: '#ffffff', life: '~50L', deg: 'LOW',      points: 'M0,5 Q40,6 70,18 T100,35' },
  { name: 'INTER',  color: '#79d1fc', life: 'VAR',  deg: 'VARIABLE', points: 'M0,30 Q30,20 50,25 T100,20' },
];

export const MODEL_OBSERVATIONS = [
  { label: 'obs[0] lap_number',    value: 0.60, color: '#79d1fc' },
  { label: 'obs[1] tire_age',      value: 0.36, color: '#e8002d' },
  { label: 'obs[2] degradation',   value: 0.77, color: '#e8002d', highlight: true },
  { label: 'obs[3] track_temp',    value: 0.53, color: '#eab308' },
  { label: 'obs[4] safety_car',    value: 0.00, color: '#00e639' },
];

export const AGENT_PERFORMANCE = [
  { name: 'DQN Agent',          winRate: 61, color: '#00e639' },
  { name: 'Deg. Threshold',     winRate: 24, color: '#79d1fc' },
  { name: 'Fixed Interval 20L', winRate: 11, color: '#c6c6c7' },
  { name: 'Random Policy',      winRate:  4, color: '#555555' },
];
