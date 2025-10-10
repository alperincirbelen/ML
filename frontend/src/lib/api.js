import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const marketAPI = {
  generateData: (symbol, timeframe, numCandles = 100) =>
    axios.post(`${API}/market/generate`, { symbol, timeframe, num_candles: numCandles }),
  
  getSymbols: () => axios.get(`${API}/market/symbols`),
  
  getTimeframes: () => axios.get(`${API}/market/timeframes`),
};

export const indicatorAPI = {
  calculate: (marketData, indicatorConfig) =>
    axios.post(`${API}/indicators/calculate`, { market_data: marketData, indicator_config: indicatorConfig }),
  
  calculateMultiple: (marketData, configs) =>
    axios.post(`${API}/indicators/calculate-multiple`, { market_data: marketData, configs }),
  
  getTypes: () => axios.get(`${API}/indicators/types`),
};

export const strategyAPI = {
  list: () => axios.get(`${API}/strategies/list`),
  
  execute: (strategyId, marketData, parameters = null) =>
    axios.post(`${API}/strategies/execute`, { strategy_id: strategyId, market_data: marketData, parameters }),
};

export const backtestAPI = {
  run: (strategyId, marketData, initialCapital = 10000, positionSize = 0.1, parameters = null) =>
    axios.post(`${API}/backtest/run`, {
      strategy_id: strategyId,
      market_data: marketData,
      initial_capital: initialCapital,
      position_size: positionSize,
      parameters,
    }),
};
