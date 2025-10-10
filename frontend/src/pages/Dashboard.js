import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Badge } from '../components/ui/badge';
import CandlestickChart from '../components/CandlestickChart';
import IndicatorChart from '../components/IndicatorChart';
import SignalPanel from '../components/SignalPanel';
import BacktestResults from '../components/BacktestResults';
import { marketAPI, strategyAPI, backtestAPI, indicatorAPI } from '../lib/api';
import { TrendingUp, BarChart3, Zap, Activity } from 'lucide-react';

const Dashboard = () => {
  const [symbols, setSymbols] = useState([]);
  const [timeframes, setTimeframes] = useState([]);
  const [strategies, setStrategies] = useState([]);
  const [indicators, setIndicators] = useState([]);
  
  const [selectedSymbol, setSelectedSymbol] = useState('BTC/USDT');
  const [selectedTimeframe, setSelectedTimeframe] = useState('5m');
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [selectedIndicators, setSelectedIndicators] = useState(['RSI', 'EMA']);
  
  const [marketData, setMarketData] = useState(null);
  const [calculatedIndicators, setCalculatedIndicators] = useState({});
  const [signal, setSignal] = useState(null);
  const [backtestResult, setBacktestResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('market');

  // Load initial data
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      const [symbolsRes, timeframesRes, strategiesRes, indicatorsRes] = await Promise.all([
        marketAPI.getSymbols(),
        marketAPI.getTimeframes(),
        strategyAPI.list(),
        indicatorAPI.getTypes(),
      ]);
      
      setSymbols(symbolsRes.data.symbols);
      setTimeframes(timeframesRes.data.timeframes);
      setStrategies(strategiesRes.data.strategies);
      setIndicators(indicatorsRes.data.indicators);
      
      if (strategiesRes.data.strategies.length > 0) {
        setSelectedStrategy(strategiesRes.data.strategies[0].id);
      }
    } catch (error) {
      console.error('Error loading initial data:', error);
    }
  };

  const loadMarketData = async () => {
    setLoading(true);
    try {
      const response = await marketAPI.generateData(selectedSymbol, selectedTimeframe, 200);
      setMarketData(response.data);
      
      // Auto-calculate default indicators
      await calculateIndicators(response.data);
    } catch (error) {
      console.error('Error loading market data:', error);
    } finally {
      setLoading(false);
    }
  };

  const calculateIndicators = async (data = marketData) => {
    if (!data) return;
    
    try {
      const configs = [
        { type: 'rsi', period: 14 },
        { type: 'ema', period: 9 },
        { type: 'ema', period: 21 },
      ];
      
      const response = await indicatorAPI.calculateMultiple(data, configs);
      setCalculatedIndicators(response.data.indicators);
    } catch (error) {
      console.error('Error calculating indicators:', error);
    }
  };

  const executeStrategy = async () => {
    if (!marketData || !selectedStrategy) return;
    
    setLoading(true);
    try {
      const response = await strategyAPI.execute(selectedStrategy, marketData);
      setSignal(response.data);
      setActiveTab('signals');
    } catch (error) {
      console.error('Error executing strategy:', error);
    } finally {
      setLoading(false);
    }
  };

  const runBacktest = async () => {
    if (!marketData || !selectedStrategy) return;
    
    setLoading(true);
    try {
      const response = await backtestAPI.run(selectedStrategy, marketData);
      setBacktestResult(response.data);
      setActiveTab('backtest');
    } catch (error) {
      console.error('Error running backtest:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900">
      {/* Header */}
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-md">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-white">MoonLight AI</h1>
                <p className="text-sm text-gray-400">Advanced Trading Intelligence</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              <Badge variant="outline" className="text-green-400 border-green-400">
                <Activity className="w-3 h-3 mr-1" />
                Live
              </Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container mx-auto px-6 py-6 space-y-6">
        {/* Control Panel */}
        <Card className="bg-black/40 backdrop-blur-md border-white/10">
          <CardHeader>
            <CardTitle className="text-white">Trading Controls</CardTitle>
            <CardDescription className="text-gray-400">Configure your trading parameters</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">Symbol</label>
                <Select value={selectedSymbol} onValueChange={setSelectedSymbol}>
                  <SelectTrigger className="bg-white/5 border-white/10 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {symbols.map((s) => (
                      <SelectItem key={s.symbol} value={s.symbol}>
                        {s.symbol}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">Timeframe</label>
                <Select value={selectedTimeframe} onValueChange={setSelectedTimeframe}>
                  <SelectTrigger className="bg-white/5 border-white/10 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {timeframes.map((tf) => (
                      <SelectItem key={tf.value} value={tf.value}>
                        {tf.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">Strategy</label>
                <Select value={selectedStrategy} onValueChange={setSelectedStrategy}>
                  <SelectTrigger className="bg-white/5 border-white/10 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {strategies.map((s) => (
                      <SelectItem key={s.id} value={s.id}>
                        {s.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">&nbsp;</label>
                <Button 
                  onClick={loadMarketData} 
                  disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Load Data
                </Button>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium text-gray-300">&nbsp;</label>
                <Button 
                  onClick={executeStrategy} 
                  disabled={loading || !marketData}
                  className="w-full bg-purple-600 hover:bg-purple-700"
                >
                  <Zap className="w-4 h-4 mr-2" />
                  Execute
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Main Dashboard Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="bg-black/40 backdrop-blur-md border border-white/10">
            <TabsTrigger value="market">Market Data</TabsTrigger>
            <TabsTrigger value="indicators">Indicators</TabsTrigger>
            <TabsTrigger value="signals">Signals</TabsTrigger>
            <TabsTrigger value="backtest">Backtest</TabsTrigger>
          </TabsList>

          <TabsContent value="market" className="space-y-4">
            <Card className="bg-black/40 backdrop-blur-md border-white/10">
              <CardHeader>
                <CardTitle className="text-white">Price Chart</CardTitle>
                <CardDescription className="text-gray-400">
                  {selectedSymbol} - {selectedTimeframe}
                </CardDescription>
              </CardHeader>
              <CardContent>
                {marketData ? (
                  <CandlestickChart data={marketData.data} />
                ) : (
                  <div className="h-96 flex items-center justify-center text-gray-400">
                    Click "Load Data" to view chart
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="indicators" className="space-y-4">
            <IndicatorChart 
              marketData={marketData} 
              indicators={calculatedIndicators} 
            />
          </TabsContent>

          <TabsContent value="signals" className="space-y-4">
            <SignalPanel signal={signal} marketData={marketData} />
          </TabsContent>

          <TabsContent value="backtest" className="space-y-4">
            <BacktestResults 
              result={backtestResult} 
              onRunBacktest={runBacktest} 
              loading={loading}
              hasData={!!marketData}
            />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default Dashboard;
