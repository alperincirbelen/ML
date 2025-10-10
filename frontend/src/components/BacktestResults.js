import React from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, PieChart, Pie, Cell } from 'recharts';
import { TrendingUp, TrendingDown, DollarSign, Percent, Activity } from 'lucide-react';

const BacktestResults = ({ result, onRunBacktest, loading, hasData }) => {
  if (!result) {
    return (
      <Card className="bg-black/40 backdrop-blur-md border-white/10">
        <CardHeader>
          <CardTitle className="text-white">Backtest Results</CardTitle>
          <CardDescription className="text-gray-400">
            Test your strategy on historical data
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64 flex flex-col items-center justify-center space-y-4">
            <p className="text-gray-400 text-center">
              Run a backtest to see performance metrics
            </p>
            <Button 
              onClick={onRunBacktest}
              disabled={loading || !hasData}
              className="bg-purple-600 hover:bg-purple-700"
            >
              {loading ? 'Running...' : 'Run Backtest'}
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  const isProfit = result.roi_percent >= 0;

  // Prepare chart data
  const performanceData = [
    { name: 'Winning', value: result.winning_trades, color: '#10b981' },
    { name: 'Losing', value: result.losing_trades, color: '#ef4444' },
  ];

  const profitData = [
    { name: 'Profit', value: result.total_profit, color: '#10b981' },
    { name: 'Loss', value: result.total_loss, color: '#ef4444' },
  ];

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-green-900/40 to-black/40 backdrop-blur-md border-green-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-green-300 text-sm mb-1">ROI</p>
                <p className={`text-2xl font-bold ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                  {result.roi_percent > 0 ? '+' : ''}{result.roi_percent}%
                </p>
              </div>
              <div className={`w-12 h-12 rounded-full flex items-center justify-center ${isProfit ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
                {isProfit ? <TrendingUp className="w-6 h-6 text-green-400" /> : <TrendingDown className="w-6 h-6 text-red-400" />}
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-blue-900/40 to-black/40 backdrop-blur-md border-blue-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-blue-300 text-sm mb-1">Final Capital</p>
                <p className="text-2xl font-bold text-white">
                  ${result.final_capital.toLocaleString()}
                </p>
              </div>
              <div className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center">
                <DollarSign className="w-6 h-6 text-blue-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-purple-900/40 to-black/40 backdrop-blur-md border-purple-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-purple-300 text-sm mb-1">Win Rate</p>
                <p className="text-2xl font-bold text-white">
                  {result.win_rate}%
                </p>
              </div>
              <div className="w-12 h-12 rounded-full bg-purple-500/20 flex items-center justify-center">
                <Percent className="w-6 h-6 text-purple-400" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-gradient-to-br from-yellow-900/40 to-black/40 backdrop-blur-md border-yellow-500/20">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-yellow-300 text-sm mb-1">Total Trades</p>
                <p className="text-2xl font-bold text-white">
                  {result.total_trades}
                </p>
              </div>
              <div className="w-12 h-12 rounded-full bg-yellow-500/20 flex items-center justify-center">
                <Activity className="w-6 h-6 text-yellow-400" />
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Performance Chart */}
        <Card className="bg-black/40 backdrop-blur-md border-white/10">
          <CardHeader>
            <CardTitle className="text-white">Trade Distribution</CardTitle>
            <CardDescription className="text-gray-400">
              Winning vs Losing trades
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={performanceData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="value"
                >
                  {performanceData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ background: 'rgba(0,0,0,0.9)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '8px' }}
                />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Profit/Loss Chart */}
        <Card className="bg-black/40 backdrop-blur-md border-white/10">
          <CardHeader>
            <CardTitle className="text-white">Profit & Loss</CardTitle>
            <CardDescription className="text-gray-400">
              Total P&L breakdown
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={profitData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                <XAxis 
                  dataKey="name" 
                  stroke="rgba(255,255,255,0.5)"
                  tick={{ fill: 'rgba(255,255,255,0.7)' }}
                />
                <YAxis 
                  stroke="rgba(255,255,255,0.5)"
                  tick={{ fill: 'rgba(255,255,255,0.7)' }}
                />
                <Tooltip 
                  contentStyle={{ background: 'rgba(0,0,0,0.9)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '8px', color: 'white' }}
                />
                <Bar dataKey="value" fill="#8884d8">
                  {profitData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Details Table */}
      <Card className="bg-black/40 backdrop-blur-md border-white/10">
        <CardHeader>
          <CardTitle className="text-white">Detailed Metrics</CardTitle>
          <CardDescription className="text-gray-400">
            Complete performance breakdown
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
            <div className="p-4 bg-white/5 rounded-lg">
              <p className="text-gray-400 text-sm mb-1">Strategy</p>
              <p className="text-white font-medium">{result.strategy_id}</p>
            </div>
            <div className="p-4 bg-white/5 rounded-lg">
              <p className="text-gray-400 text-sm mb-1">Symbol</p>
              <p className="text-white font-medium">{result.symbol}</p>
            </div>
            <div className="p-4 bg-white/5 rounded-lg">
              <p className="text-gray-400 text-sm mb-1">Timeframe</p>
              <p className="text-white font-medium">{result.timeframe}</p>
            </div>
            <div className="p-4 bg-white/5 rounded-lg">
              <p className="text-gray-400 text-sm mb-1">Initial Capital</p>
              <p className="text-white font-medium">${result.initial_capital.toLocaleString()}</p>
            </div>
            <div className="p-4 bg-white/5 rounded-lg">
              <p className="text-gray-400 text-sm mb-1">Profit Factor</p>
              <p className="text-white font-medium">{result.profit_factor}</p>
            </div>
            <div className="p-4 bg-white/5 rounded-lg">
              <p className="text-gray-400 text-sm mb-1">Net P&L</p>
              <p className={`font-bold ${isProfit ? 'text-green-400' : 'text-red-400'}`}>
                ${(result.total_profit - result.total_loss).toFixed(2)}
              </p>
            </div>
          </div>

          {/* Action Button */}
          <div className="mt-6 flex justify-center">
            <Button 
              onClick={onRunBacktest}
              disabled={loading}
              className="bg-purple-600 hover:bg-purple-700"
            >
              Run New Backtest
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default BacktestResults;
