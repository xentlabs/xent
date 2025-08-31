import React from 'react';

interface ProgressBarProps {
  completed: number;
  total: number;
  percentage: number;
}

export function ProgressBar({ completed, total, percentage }: ProgressBarProps) {
  return (
    <div>
      <div className="flex justify-between text-sm text-gray-600 mb-1">
        <span>Progress</span>
        <span>{completed} / {total} games</span>
      </div>
      <div className="w-full bg-gray-200 rounded-full h-2.5">
        <div 
          className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="text-right text-sm text-gray-600 mt-1">
        {percentage.toFixed(1)}%
      </div>
    </div>
  );
}