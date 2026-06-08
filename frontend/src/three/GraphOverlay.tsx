import { Html } from '@react-three/drei';
import type { Gambit, Planet } from '../api/types';

interface GraphOverlayProps {
  planets: Planet[];
  gambits: Gambit[];
}

const styles: Record<Gambit['kind'], { color: string; label: string; scale: number }> = {
  GAMBIT: { color: '#facc15', label: 'Gambit', scale: 0.16 },
  SIEGE: { color: '#fb7185', label: 'Siege', scale: 0.15 },
  CHOKEPOINT: { color: '#22d3ee', label: 'Choke', scale: 0.13 }
};

export function GraphOverlay({ planets, gambits }: GraphOverlayProps): JSX.Element {
  const byIndex = new Map(planets.map((planet) => [planet.index, planet]));
  return (
    <group>
      {gambits.map((gambit) => {
        const planet = byIndex.get(gambit.targetIndex);
        if (planet === undefined) {
          return null;
        }
        const style = styles[gambit.kind];
        return (
          <group key={`${gambit.kind}-${gambit.sourceIndex}-${gambit.targetIndex}`} position={[planet.position.x * 6, planet.position.y * 6, 0.16]}>
            <mesh scale={style.scale}>
              <ringGeometry args={[0.72, 1, 32]} />
              <meshBasicMaterial color={style.color} transparent opacity={0.9} />
            </mesh>
            <Html distanceFactor={9} position={[0.18, -0.18, 0]}>
              <div className="max-w-44 rounded border bg-black/85 px-2 py-1 text-[10px] uppercase tracking-[0.16em] shadow-lg" style={{ borderColor: style.color, color: style.color }} title={gambit.note}>
                {style.label}
              </div>
            </Html>
          </group>
        );
      })}
    </group>
  );
}
