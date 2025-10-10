import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

const IndicatorChart = ({ marketData, indicators }) => {
  if (!marketData || !indicators || Object.keys(indicators).length === 0) {
    return (
      <Card className="bg-black/40 backdrop-blur-md border-white/10">
        <CardHeader>
          <CardTitle className="text-white">Technical Indicators</CardTitle>
          <CardDescription className="text-gray-400">No indicators calculated yet</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-96 flex items-center justify-center text-gray-400">
            Load market data to view indicators
          </div>
        </CardContent>
      </Card>
    );
  }

  // Prepare chart data
  const chartData = marketData.data.map((candle, index) => {
    const dataPoint = {
      index,
      time: new Date(candle.timestamp).toLocaleTimeString(),
      price: candle.close,
    };

    // Add indicator values
    Object.keys(indicators).forEach(key => {
      const indicator = indicators[key];
      if (indicator.values && indicator.values[index] !== undefined) {
        dataPoint[key] = indicator.values[index];
      }
    });

    return dataPoint;
  });

  const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-black/90 border border-white/20 rounded-lg p-3 text-white text-sm">
          <p className="font-medium mb-1">{payload[0].payload.time}</p>
          {payload.map((entry, index) => (
            <p key={index} style={{ color: entry.color }}>
              {entry.name}: {entry.value?.toFixed(2)}
            </p>
          ))}
        </div>
      );
    }
    return null;
  };

  const colors = ['#10b981', '#3b82f6', '#f59e0b', '#8b5cf6', '#ef4444'];

  return (
    <Card className="bg-black/40 backdrop-blur-md border-white/10">
      <CardHeader>
        <CardTitle className="text-white">Technical Indicators</CardTitle>
        <CardDescription className="text-gray-400">
          {Object.keys(indicators).length} indicators active
        </CardDescription>
      </CardHeader>
      <CardContent>
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
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend 
                wrapperStyle={{ color: 'white' }}
                iconType="line"
              />
              <Line 
                type="monotone" 
                dataKey="price" 
                stroke="#ffffff" 
                strokeWidth={2}
                dot={false}
                name="Price"
              />
              {Object.keys(indicators).map((key, index) => (
                <Line
                  key={key}
                  type="monotone"
                  dataKey={key}
                  stroke={colors[index % colors.length]}
                  strokeWidth={2}
                  dot={false}
                  name={key}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
};

export default IndicatorChart;
