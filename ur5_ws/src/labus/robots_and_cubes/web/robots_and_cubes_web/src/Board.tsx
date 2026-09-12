import type { Snapshot } from './types';

type BoardProps = {
  snapshot: Snapshot;
  interactive?: boolean;
  disabled?: boolean;
  onCubeSelect?: (cubeId: string) => void;
};

export function Board({ snapshot, interactive = false, disabled = false, onCubeSelect }: BoardProps) {
  const cells = Array.from(
    { length: snapshot.board.rows * snapshot.board.columns },
    (_, index) => ({
      column: index % snapshot.board.columns,
      row: snapshot.board.rows - 1 - Math.floor(index / snapshot.board.columns),
    }),
  );
  return <div
    className={`board mode-${snapshot.mode ?? 'idle'}`}
    style={{
      gridTemplateColumns: `repeat(${snapshot.board.columns}, minmax(0, 1fr))`,
      gridTemplateRows: `repeat(${snapshot.board.rows}, minmax(0, 1fr))`,
    }}
    aria-label="Igraća ploča"
  >
    {cells.map((cell) => {
      const cube = snapshot.cubes.find(
        (item) => !item.removed && item.column === cell.column && item.row === cell.row,
      );
      const origin = snapshot.origin?.column === cell.column && snapshot.origin?.row === cell.row;
      if (interactive && cube) {
        return <button
          className="cell selectable-cell"
          key={`${cell.column}-${cell.row}`}
          type="button"
          disabled={disabled}
          onClick={() => onCubeSelect?.(cube.id)}
        >
          <span className={`cube ${cube.visual_kind}`}>{cube.symbol}</span>
        </button>;
      }
      return <div className="cell" key={`${cell.column}-${cell.row}`}>
        {origin && <OriginAxes snapshot={snapshot}/>} {cube && <span className={`cube ${cube.visual_kind}`}>{cube.symbol}</span>}
      </div>;
    })}
  </div>;
}

function OriginAxes({ snapshot }: { snapshot: Snapshot }) {
  const origin = snapshot.origin;
  if (!origin) return null;
  const axes = axisDirections(origin.rotation_deg, origin.handedness);
  const end = (axis: AxisDirection, length: number) => ({
    x: 50 + axis.column * length,
    y: 50 - axis.row * length,
  });
  const xEnd = end(axes.x, 21);
  const yEnd = end(axes.y, 21);
  const xLabel = end(axes.x, 31);
  const yLabel = end(axes.y, 31);
  return <svg className="origin-axes" viewBox="0 0 100 100" role="img" aria-label="Ishodište s X i Y osima">
    <defs>
      <marker id="x-axis-arrow" markerWidth="4" markerHeight="4" refX="3.3" refY="2" orient="auto">
        <path d="M 0 0 L 4 2 L 0 4 z" fill="currentColor"/>
      </marker>
      <marker id="y-axis-arrow" markerWidth="4" markerHeight="4" refX="3.3" refY="2" orient="auto">
        <path d="M 0 0 L 4 2 L 0 4 z" fill="currentColor"/>
      </marker>
    </defs>
    <g className="axis-x">
      <line x1="50" y1="50" x2={xEnd.x} y2={xEnd.y} markerEnd="url(#x-axis-arrow)"/>
      <text x={xLabel.x} y={xLabel.y}>X</text>
    </g>
    <g className="axis-y">
      <line x1="50" y1="50" x2={yEnd.x} y2={yEnd.y} markerEnd="url(#y-axis-arrow)"/>
      <text x={yLabel.x} y={yLabel.y}>Y</text>
    </g>
    <circle className="origin-point" cx="50" cy="50" r="7"/>
  </svg>;
}

type AxisDirection = { column: number; row: number };

export function axisDirections(rotationDeg: number, handedness: string): {
  x: AxisDirection;
  y: AxisDirection;
} {
  const rotation = ((rotationDeg % 360) + 360) % 360;
  const matrix = {
    0: [[1, 0], [0, 1]],
    90: [[0, -1], [1, 0]],
    180: [[-1, 0], [0, -1]],
    270: [[0, 1], [-1, 0]],
  }[rotation as 0 | 90 | 180 | 270];
  if (!matrix) throw new Error(`Unsupported origin rotation: ${rotationDeg}`);
  const ySign = handedness === 'left' ? -1 : 1;
  return {
    x: direction(matrix[0][0], matrix[1][0]),
    y: direction(matrix[0][1] * ySign, matrix[1][1] * ySign),
  };
}

function direction(column: number, row: number): AxisDirection {
  return { column: column || 0, row: row || 0 };
}
