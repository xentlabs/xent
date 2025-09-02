import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { LineChartData } from '../../types/benchmark';

interface ProgressLineChartProps {
  data: LineChartData[];
  title?: string;
  height?: number;
  className?: string;
  yAxisLabel?: string;
  xAxisLabel?: string;
}

// Color palette for different players
const COLORS = [
  '#3b82f6', // blue
  '#10b981', // emerald  
  '#f59e0b', // amber
  '#ef4444', // red
  '#8b5cf6', // violet
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#f97316', // orange
  '#ec4899', // pink
  '#6b7280', // gray
];

export default function ProgressLineChart({ 
  data, 
  title, 
  height = 400, 
  className = "",
  yAxisLabel = "Score",
  xAxisLabel = "Iteration"
}: ProgressLineChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height: height/4 }}>
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }

  // Extract player names from the first data point (excluding 'iteration')
  const playerNames = Object.keys(data[0] || {}).filter(key => key !== 'iteration');
  
  return (
    <div className={`w-full ${className}`}>
      {title && (
        <h3 className="text-lg font-semibold mb-4 text-gray-800">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart
          data={data}
          margin={{
            top: 20,
            right: 30,
            left: 20,
            bottom: 20,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis 
            dataKey="iteration" 
            fontSize={12}
            className="fill-gray-600"
            label={{ 
              value: xAxisLabel, 
              position: 'insideBottom', 
              offset: -10,
              style: { textAnchor: 'middle', fill: '#6b7280' }
            }}
          />
          <YAxis 
            fontSize={12}
            className="fill-gray-600"
            label={{ 
              value: yAxisLabel, 
              angle: -90, 
              position: 'insideLeft',
              style: { textAnchor: 'middle', fill: '#6b7280' }
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              fontSize: '14px',
            }}
            formatter={(value: number, name: string) => [
              value?.toFixed(2) ?? 'N/A', 
              name
            ]}
            labelFormatter={(label: number) => `${xAxisLabel}: ${label}`}
            labelStyle={{ color: '#374151', fontWeight: 'bold' }}
          />
          <Legend 
            wrapperStyle={{ 
              paddingTop: '20px',
              fontSize: '14px'
            }}
          />
          {playerNames.map((playerName, index) => (
            <Line
              key={playerName}
              type="monotone"
              dataKey={playerName}
              stroke={COLORS[index % COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}