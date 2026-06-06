import type { Planet } from '../api/types';

interface SupplyLinesProps {
  planets: Planet[];
}

export function SupplyLines({ planets }: SupplyLinesProps): JSX.Element {
  const byIndex = new Map(planets.map((planet) => [planet.index, planet]));
  const segments = planets.flatMap((planet) =>
    planet.waypoints
      .map((targetIndex) => byIndex.get(targetIndex))
      .filter((target): target is Planet => target !== undefined && planet.index < target.index)
      .map((target) => ({ source: planet, target }))
  );

  return (
    <group>
      {segments.map(({ source, target }) => {
        const dx = (target.position.x - source.position.x) * 6;
        const dy = (target.position.y - source.position.y) * 6;
        const length = Math.sqrt(dx * dx + dy * dy);
        const angle = Math.atan2(dy, dx);
        return (
          <mesh
            key={`${source.index}-${target.index}`}
            position={[((source.position.x + target.position.x) / 2) * 6, ((source.position.y + target.position.y) / 2) * 6, -0.03]}
            rotation={[0, 0, angle]}
          >
            <boxGeometry args={[length, 0.012, 0.012]} />
            <meshBasicMaterial color="#164e63" transparent opacity={0.55} />
          </mesh>
        );
      })}
    </group>
  );
}
