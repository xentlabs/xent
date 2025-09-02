import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { ChartData } from '../../types/benchmark';

interface ScoreBarChartProps {
  data: ChartData[];
  title?: string;
  height?: number;
  className?: string;
}

export default function ScoreBarChart({ 
  data, 
  title, 
  height = 400, 
  className = "" 
}: ScoreBarChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height: height/4 }}>
        <p className="text-gray-500">No data available</p>
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`}>
      {title && (
        <h3 className="text-lg font-semibold mb-4 text-gray-800">{title}</h3>
      )}
      <ResponsiveContainer width="100%" height={height}>
        <BarChart
          data={data}
          margin={{
            top: 20,
            right: 30,
            left: 20,
            bottom: 60,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
          <XAxis 
            dataKey="name" 
            angle={-45}
            textAnchor="end"
            height={60}
            fontSize={12}
            className="fill-gray-600"
          />
          <YAxis 
            fontSize={12}
            className="fill-gray-600"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e2e8f0',
              borderRadius: '6px',
              boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              fontSize: '14px',
            }}
            formatter={(value: number) => [value.toFixed(2), 'Score']}
            labelStyle={{ color: '#374151', fontWeight: 'bold' }}
          />
          <Bar 
            dataKey="value" 
            fill="#3b82f6"
            radius={[2, 2, 0, 0]}
            className="hover:opacity-80 transition-opacity"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}