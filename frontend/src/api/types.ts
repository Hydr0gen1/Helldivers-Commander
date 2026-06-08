export type Faction = 1 | 2 | 3 | 4;

export interface Position {
  x: number;
  y: number;
}

export interface Statistics {
  missionsWon: number;
  missionsLost: number;
  missionTime: number;
  terminidKills: number;
  automatonKills: number;
  illuminateKills: number;
  bulletsFired: number;
  bulletsHit: number;
  timePlayed: number;
  deaths: number;
  revives: number;
  friendlies: number;
  missionSuccessRate: number;
  accuracy: number;
  playerCount: number;
}

export interface Derived {
  libRatePctPerHr: number | null;
  decayPctPerHr: number;
  etaHours: number | null;
  confidence: number;
  trend: 'accelerating' | 'steady' | 'stalling' | 'losing';
}

export interface PlanetHistoryPoint {
  ts: string;
  liberationPct: number;
  players: number;
}

export interface PlanetHistoryResponse { history: PlanetHistoryPoint[]; }

export interface Planet {
  index: number;
  name: string;
  sector: string;
  biome: Record<string, unknown> | null;
  position: Position;
  waypoints: number[];
  maxHealth: number;
  health: number;
  liberationPct: number;
  disabled: boolean;
  regenPerSecond: number;
  owner: number;
  currentOwner: string;
  players: number;
  statistics: Statistics;
  attacking: number[];
  event: Record<string, unknown> | null;
  derived: Derived | null;
}

export interface Task {
  type: number;
  values: number[];
  valueTypes: number[];
}

export interface Reward {
  type: number;
  amount: number;
  id32: number;
}

export interface Order {
  id: number;
  title: string;
  briefing: string;
  description: string;
  type: number;
  flags: number;
  expiration: string;
  progress: number[];
  tasks: Task[];
  rewards: Reward[];
  winProbability: number | null;
}

export interface Dispatch {
  id: number;
  published: string;
  type: number;
  message: string | null;
}

export interface War {
  warId: number;
  time: string;
  impactMultiplier: number;
  statistics: Statistics;
}

export interface Gambit {
  kind: 'GAMBIT' | 'SIEGE' | 'CHOKEPOINT';
  sourceIndex: number;
  targetIndex: number;
  note: string;
}

export interface PlanetsResponse { planets: Planet[]; }
export interface GambitsResponse { gambits: Gambit[]; }
export interface OrdersResponse { orders: Order[]; }
export interface DispatchesResponse { dispatches: Dispatch[]; }
export interface CampaignsResponse { campaigns: Record<string, unknown>[]; }
export interface BriefingResponse { text: string; generatedAt: string; }
export interface HealthResponse { sources: Record<string, 'up' | 'down' | 'open'>; lastIngest: string | null; }
