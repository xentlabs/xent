interface TokenVisualizationProps {
  perTokenXent: any; // This can be a complex structure from the backend
}

export default function TokenVisualization({ perTokenXent }: TokenVisualizationProps) {
  // Handle different formats of perTokenXent
  let tokens: Array<[string, number]> = [];
  let totalScore = 0;

  if (Array.isArray(perTokenXent)) {
    // If it's already an array of [token, score] pairs
    tokens = perTokenXent;
    totalScore = tokens.reduce((sum, [_, score]) => sum + score, 0);
  } else if (perTokenXent && typeof perTokenXent === 'object') {
    // If it has a total_xent method or property
    if (perTokenXent.total_xent) {
      totalScore = typeof perTokenXent.total_xent === 'function' 
        ? perTokenXent.total_xent() 
        : perTokenXent.total_xent;
    }
    if (perTokenXent.pairs) {
      tokens = perTokenXent.pairs;
    }
  } else if (typeof perTokenXent === 'number') {
    totalScore = perTokenXent;
  }

  // Color scale for scores (lower is better for cross-entropy)
  const getColorForScore = (score: number): string => {
    if (score < 2) return '#4CAF50';      // Green - very good
    if (score < 4) return '#8BC34A';      // Light green - good
    if (score < 6) return '#FFC107';      // Yellow - okay
    if (score < 8) return '#FF9800';      // Orange - poor
    return '#f44336';                      // Red - very poor
  };

  return (
    <div style={{ 
      marginBottom: '15px', 
      padding: '15px', 
      backgroundColor: '#e3f2fd', 
      borderRadius: '5px',
      border: '1px solid #2196F3'
    }}>
      <div style={{ marginBottom: '10px' }}>
        <strong>🎯 Reward - Total Score: {totalScore.toFixed(2)}</strong>
      </div>
      
      {tokens.length > 0 && (
        <div>
          <div style={{ fontSize: '12px', color: '#666', marginBottom: '8px' }}>
            Per-token cross-entropy:
          </div>
          <div style={{ 
            display: 'flex', 
            flexWrap: 'wrap', 
            gap: '5px',
            fontFamily: 'monospace',
            fontSize: '12px'
          }}>
            {tokens.map(([token, score], index) => (
              <div
                key={index}
                style={{
                  padding: '4px 8px',
                  backgroundColor: getColorForScore(score),
                  color: 'white',
                  borderRadius: '3px',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center'
                }}
                title={`Token: "${token}", Score: ${score.toFixed(2)}`}
              >
                <div style={{ fontWeight: 'bold' }}>{token || '⎵'}</div>
                <div style={{ fontSize: '10px' }}>{score.toFixed(2)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      
      <div style={{ marginTop: '10px', fontSize: '11px', color: '#666' }}>
        Lower scores are better (indicates lower cross-entropy)
      </div>
    </div>
  );
}