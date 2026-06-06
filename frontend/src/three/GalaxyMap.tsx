import { Canvas } from '@react-three/fiber';
import { OrbitControls, Stars } from '@react-three/drei';
import type { Planet as PlanetModel } from '../api/types';
import { Planet } from './Planet';
import { SupplyLines } from './SupplyLines';

interface GalaxyMapProps {
  planets: PlanetModel[];
  selected: PlanetModel | null;
  onSelect: (planet: PlanetModel) => void;
}

export function GalaxyMap({ planets, selected, onSelect }: GalaxyMapProps): JSX.Element {
  return (
    <div className="h-[68vh] min-h-[520px] overflow-hidden rounded-2xl border border-cyan-500/30 bg-slate-950 shadow-2xl shadow-cyan-950/40">
      <Canvas camera={{ position: [0, 0, 10], fov: 55 }}>
        <color attach="background" args={['#020617']} />
        <ambientLight intensity={0.45} />
        <pointLight position={[0, 0, 6]} intensity={1.5} color="#67e8f9" />
        <Stars radius={60} depth={20} count={1600} factor={2.5} fade speed={0.4} />
        <SupplyLines planets={planets} />
        {planets.map((planet) => (
          <Planet key={planet.index} planet={planet} selected={selected?.index === planet.index} onSelect={onSelect} />
        ))}
        <OrbitControls enablePan enableZoom minDistance={4} maxDistance={18} />
      </Canvas>
    </div>
  );
}
