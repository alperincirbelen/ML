import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { TrendingUp, TrendingDown, Minus, Zap } from 'lucide-react';

const SignalPanel = ({ signal, marketData }) => {
  if (!signal) {
    return (
      <Card className="bg-black/40 backdrop-blur-md border-white/10">
        <CardHeader>
          <CardTitle className="text-white">Trading Signal</CardTitle>
          <CardDescription className="text-gray-400">No signal generated yet</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex items-center justify-center text-gray-400">
            Execute a strategy to generate signals
          </div>
        </CardContent>
      </Card>
    );
  }

  const getSignalColor = (type) => {
    switch (type) {
      case 'BUY':
        return 'text-green-400 border-green-400';
      case 'SELL':
        return 'text-red-400 border-red-400';
      default:
        return 'text-gray-400 border-gray-400';
    }
  };

  const getSignalIcon = (type) => {
    switch (type) {
      case 'BUY':
        return <TrendingUp className="w-12 h-12" />;
      case 'SELL':
        return <TrendingDown className="w-12 h-12" />;
      default:
        return <Minus className="w-12 h-12" />;
    }
  };

  const getStrengthColor = (strength) => {
    switch (strength) {
      case 'strong':
        return 'bg-purple-500';
      case 'moderate':
        return 'bg-yellow-500';
      default:
        return 'bg-gray-500';
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      {/* Signal Card */}
      <Card className="bg-black/40 backdrop-blur-md border-white/10">
        <CardHeader>
          <CardTitle className="text-white">Current Signal</CardTitle>
          <CardDescription className="text-gray-400">
            {signal.strategy_name} - {signal.timeframe}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {/* Signal Type */}
            <div className="flex flex-col items-center justify-center space-y-4 py-8">
              <div className={getSignalColor(signal.signal_type)}>
                {getSignalIcon(signal.signal_type)}
              </div>
              <Badge 
                variant="outline" 
                className={`text-2xl px-6 py-2 ${getSignalColor(signal.signal_type)}`}
              >
                {signal.signal_type}
              </Badge>
            </div>

            {/* Signal Details */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-white/5 rounded-lg p-4">
                <p className="text-gray-400 text-sm mb-1">Price</p>
                <p className="text-white text-xl font-bold">${signal.price?.toFixed(2)}</p>
              </div>
              <div className="bg-white/5 rounded-lg p-4">
                <p className="text-gray-400 text-sm mb-1">Confidence</p>
                <p className="text-white text-xl font-bold">{(signal.confidence * 100).toFixed(1)}%</p>
              </div>
            </div>

            {/* Strength Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Strength</span>
                <span className="text-white font-medium uppercase">{signal.strength}</span>
              </div>
              <div className="w-full bg-white/10 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full ${getStrengthColor(signal.strength)}`}
                  style={{ width: `${signal.confidence * 100}%` }}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Indicators Card */}
      <Card className="bg-black/40 backdrop-blur-md border-white/10">
        <CardHeader>
          <CardTitle className="text-white">Signal Indicators</CardTitle>
          <CardDescription className="text-gray-400">Technical analysis used</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Object.keys(signal.indicators).map((key) => (
              <div key={key} className="flex justify-between items-center p-3 bg-white/5 rounded-lg">
                <span className="text-gray-300 font-medium">{key}</span>
                <span className="text-white font-mono">{signal.indicators[key]?.toFixed(2)}</span>
              </div>
            ))}

            {/* Timestamp */}
            <div className="mt-6 pt-4 border-t border-white/10">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-400">Generated</span>
                <span className="text-white font-mono">
                  {new Date(signal.timestamp).toLocaleString()}
                </span>
              </div>
              <div className="flex items-center justify-between text-sm mt-2">
                <span className="text-gray-400">Symbol</span>
                <span className="text-white font-bold">{signal.symbol}</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default SignalPanel;
