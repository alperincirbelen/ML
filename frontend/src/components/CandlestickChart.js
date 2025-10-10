import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const CandlestickChart = ({ data }) => {
  if (!data || data.length === 0) {
    return <div className="h-96 flex items-center justify-center text-gray-400">No data available</div>;
  }

  // Transform data for line chart (simplified candlestick visualization)
  const chartData = data.map((candle, index) => ({
    index,
    time: new Date(candle.timestamp).toLocaleTimeString(),
    close: candle.close,
    high: candle.high,
    low: candle.low,
    open: candle.open,
  }));

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-black/90 border border-white/20 rounded-lg p-3 text-white text-sm">
          <p className="font-medium mb-1">{data.time}</p>
          <p className="text-green-400">O: ${data.open?.toFixed(2)}</p>
          <p className="text-blue-400">H: ${data.high?.toFixed(2)}</p>
          <p className="text-red-400">L: ${data.low?.toFixed(2)}</p>
          <p className="text-yellow-400">C: ${data.close?.toFixed(2)}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="w-full h-96">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis 
            dataKey="time" 
            stroke="rgba(255,255,255,0.5)"
            tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
            interval={Math.floor(chartData.length / 10)}
          />
          <YAxis 
            stroke="rgba(255,255,255,0.5)"
            tick={{ fill: 'rgba(255,255,255,0.7)', fontSize: 12 }}
            domain={['auto', 'auto']}
          />
          <Tooltip content={<CustomTooltip />} />
          <Line 
            type="monotone" 
            dataKey="close" 
            stroke="#10b981" 
            strokeWidth={2}
            dot={false}
            animationDuration={500}
          />
          <Line 
            type="monotone" 
            dataKey="high" 
            stroke="#3b82f6" 
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={false}
            opacity={0.5}
          />
          <Line 
            type="monotone" 
            dataKey="low" 
            stroke="#ef4444" 
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={false}
            opacity={0.5}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
};

export default CandlestickChart;
