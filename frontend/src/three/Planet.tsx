import { Html } from '@react-three/drei';
import type { Planet as PlanetModel } from '../api/types';

const factionColors: Record<string, string> = {
  SUPER_EARTH: '#38bdf8',
  TERMINIDS: '#f97316',
  AUTOMATONS: '#ef4444',
  ILLUMINATE: '#a855f7',
  UNKNOWN: '#94a3b8'
};

interface PlanetProps {
  planet: PlanetModel;
  selected: boolean;
  onSelect: (planet: PlanetModel) => void;
}

export function Planet({ planet, selected, onSelect }: PlanetProps): JSX.Element {
  const color = factionColors[planet.currentOwner] ?? factionColors.UNKNOWN;
  const scale = selected ? 0.085 : 0.055 + Math.min(planet.players / 100_000, 0.04);
  return (
    <group position={[planet.position.x * 6, planet.position.y * 6, (planet.index % 9) * 0.015]}>
      <mesh onClick={(event) => { event.stopPropagation(); onSelect(planet); }} scale={scale}>
        <sphereGeometry args={[1, 24, 24]} />
        <meshStandardMaterial color={color} emissive={color} emissiveIntensity={selected ? 0.85 : 0.35 + planet.liberationPct / 250} />
      </mesh>
      {selected ? (
        <Html distanceFactor={8} position={[0.15, 0.15, 0]}>
          <div className="rounded border border-terminal/60 bg-black/80 px-2 py-1 text-xs text-terminal shadow-lg shadow-terminal/20">
            {planet.name}
          </div>
        </Html>
      ) : null}
    </group>
  );
}
