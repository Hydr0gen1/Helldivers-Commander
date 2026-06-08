import { Canvas } from '@react-three/fiber';
import { Html, OrbitControls, Stars } from '@react-three/drei';
import type { Gambit, Planet as PlanetModel } from '../api/types';
import { Planet } from './Planet';
import { SupplyLines } from './SupplyLines';

interface GalaxyMapProps {
  planets: PlanetModel[];
  selected: PlanetModel | null;
  onSelect: (planet: PlanetModel) => void;
  gambits: Gambit[];
  showGraphIntel: boolean;
  onToggleGraphIntel: () => void;
}

const markerColors: Record<Gambit['kind'], string> = {
  GAMBIT: '#facc15',
  SIEGE: '#fb7185',
  CHOKEPOINT: '#22d3ee'
};

const markerLabels: Record<Gambit['kind'], string> = {
  GAMBIT: 'G',
  SIEGE: 'S',
  CHOKEPOINT: 'C'
};

export function GalaxyMap({ planets, selected, onSelect, gambits, showGraphIntel, onToggleGraphIntel }: GalaxyMapProps): JSX.Element {
  return (
    <div className="relative h-[68vh] min-h-[520px] overflow-hidden rounded-2xl border border-cyan-500/30 bg-slate-950 shadow-2xl shadow-cyan-950/40">
      <button
        type="button"
        onClick={onToggleGraphIntel}
        className={`absolute right-4 top-4 z-10 rounded border px-3 py-2 text-xs uppercase tracking-[0.2em] transition ${showGraphIntel ? 'border-terminal bg-terminal/15 text-terminal' : 'border-slate-600 bg-slate-950/80 text-slate-400 hover:border-cyan-500/60 hover:text-cyan-100'}`}
      >
        Graph intel {showGraphIntel ? 'on' : 'off'}
      </button>
      <Canvas camera={{ position: [0, 0, 10], fov: 55 }}>
        <color attach="background" args={['#020617']} />
        <ambientLight intensity={0.45} />
        <pointLight position={[0, 0, 6]} intensity={1.5} color="#67e8f9" />
        <Stars radius={60} depth={20} count={1600} factor={2.5} fade speed={0.4} />
        <SupplyLines planets={planets} />
        {showGraphIntel ? <GraphIntelOverlay planets={planets} gambits={gambits} /> : null}
        {planets.map((planet) => (
          <Planet key={planet.index} planet={planet} selected={selected?.index === planet.index} onSelect={onSelect} />
        ))}
        <OrbitControls enablePan enableZoom minDistance={4} maxDistance={18} />
      </Canvas>
    </div>
  );
}

function GraphIntelOverlay({ planets, gambits }: { planets: PlanetModel[]; gambits: Gambit[] }): JSX.Element {
  const byIndex = new Map(planets.map((planet) => [planet.index, planet]));
  return (
    <group>
      {gambits.map((gambit) => {
        const planet = byIndex.get(gambit.targetIndex);
        if (planet === undefined) {
          return null;
        }
        const color = markerColors[gambit.kind];
        return (
          <group key={`${gambit.kind}-${gambit.sourceIndex}-${gambit.targetIndex}`} position={[planet.position.x * 6, planet.position.y * 6, 0.22]}>
            <mesh>
              <torusGeometry args={[0.16, 0.014, 8, 36]} />
              <meshBasicMaterial color={color} transparent opacity={0.9} />
            </mesh>
            <Html distanceFactor={8} position={[0.18, 0.18, 0]}>
              <div className="rounded border bg-black/85 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.18em] shadow-lg" style={{ borderColor: color, color }} title={gambit.note}>
                {markerLabels[gambit.kind]}
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
}
