import { useState } from 'react';

interface TokenVisualizationProps {
  perTokenXent: any; // This can be a complex structure from the backend
}

const formatNumber = (num: number): string => {
  return num.toFixed(4);
};

export default function TokenVisualization({ perTokenXent }: TokenVisualizationProps) {
  const [hoveredToken, setHoveredToken] = useState<number | null>(null);

  // Handle different formats of perTokenXent
  const tokens: Array<[string, number]> = perTokenXent.pairs;
  const totalScore = tokens.reduce((sum, [_, score]) => sum + score, 0);

  // NextJS-style color calculation with tanh normalization
  const getColorStyle = (score: number): React.CSSProperties => {
    let normalizedScore = Math.tanh(score / 5);
    const opacity = Math.abs(normalizedScore);

    // Use blue/cyan colors for positive scores (higher cross-entropy)
    if (score >= 0) {
      const blueRgb = "37, 99, 235"; // blue[6]
      return {
        backgroundColor: `rgba(${blueRgb}, ${opacity})`,
      };
    } else {
      // Use red colors for negative scores (should be rare for cross-entropy)
      const redRgb = "239, 68, 68"; // red[5]
      return {
        backgroundColor: `rgba(${redRgb}, ${opacity})`,
      };
    }
  };

  if (!tokens || tokens.length === 0) {
    return (
      <div style={{ marginBottom: '15px' }}>
        <span style={{ fontSize: '12px', color: '#666' }}>
          Reward: {formatNumber(totalScore)}
        </span>
      </div>
    );
  }

  return (
    <div style={{ marginBottom: '15px' }}>
      <span style={{ fontSize: '12px', color: '#666', marginBottom: '8px', display: 'block' }}>
        Reward: {formatNumber(totalScore)}
      </span>

      <div style={{
        display: 'flex',
        flexWrap: 'wrap',
        gap: '4px',
        position: 'relative'
      }}>
        {tokens.map(([token, score], index) => (
          <span
            key={index}
            style={{
              fontFamily: 'monospace',
              fontSize: '14px',
              padding: '2px 4px',
              borderRadius: '3px',
              display: 'inline-block',
              position: 'relative',
              cursor: 'default',
              ...getColorStyle(score)
            }}
            onMouseEnter={() => setHoveredToken(index)}
            onMouseLeave={() => setHoveredToken(null)}
          >
            <span
              style={{
                mixBlendMode: 'difference',
                color: 'white',
              }}
            >
              {token || '⎵'}
            </span>

            {/* Custom tooltip */}
            {hoveredToken === index && (
              <div
                style={{
                  position: 'absolute',
                  bottom: '100%',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  marginBottom: '8px',
                  padding: '4px 8px',
                  backgroundColor: '#374151',
                  color: 'white',
                  fontSize: '12px',
                  borderRadius: '4px',
                  whiteSpace: 'nowrap',
                  zIndex: 1000,
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                }}
              >
                Score: {formatNumber(score)}

                {/* Tooltip arrow */}
                <div
                  style={{
                    position: 'absolute',
                    top: '100%',
                    left: '50%',
                    transform: 'translateX(-50%)',
                    width: 0,
                    height: 0,
                    borderLeft: '4px solid transparent',
                    borderRight: '4px solid transparent',
                    borderTop: '4px solid #374151',
                  }}
                />
              </div>
            )}
          </span>
        ))}
      </div>
    </div>
  );
}
