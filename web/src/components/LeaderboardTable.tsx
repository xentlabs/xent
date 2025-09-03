import { ChartData } from '../types/benchmark';

interface LeaderboardTableProps {
  data: ChartData[];
  title?: string;
  className?: string;
}

export default function LeaderboardTable({ 
  data, 
  title, 
  className = "" 
}: LeaderboardTableProps) {
  if (!data || data.length === 0) {
    return (
      <div className={`${className}`}>
        {title && (
          <h3 className="text-lg font-semibold mb-4 text-gray-800">{title}</h3>
        )}
        <div className="text-center py-8 text-gray-500">
          No data available
        </div>
      </div>
    );
  }

  // Sort by score descending
  const sortedData = [...data].sort((a, b) => b.value - a.value);

  return (
    <div className={`${className}`}>
      {title && (
        <h3 className="text-lg font-semibold mb-4 text-gray-800">{title}</h3>
      )}
      <div className="overflow-x-auto">
        <table className="min-w-full bg-white border border-gray-200 rounded-lg shadow-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Rank
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Player
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Score
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {sortedData.map((item, index) => (
              <tr 
                key={item.name} 
                className={index % 2 === 0 ? 'bg-white' : 'bg-gray-50'}
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  <span className={`font-semibold ${
                    index === 0 ? 'text-yellow-600' :
                    index === 1 ? 'text-gray-400' :
                    index === 2 ? 'text-amber-600' :
                    'text-gray-600'
                  }`}>
                    #{index + 1}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {item.name}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                  <span className="font-mono">
                    {item.value.toFixed(2)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}