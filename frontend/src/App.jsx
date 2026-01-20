import { useState, useEffect, useCallback } from 'react';
import StatusPanel from './components/StatusPanel';
import PositionsTable from './components/PositionsTable';
import AIReasoningFeed from './components/AIReasoningFeed';
import ConfigPanel from './components/ConfigPanel';
import ConnectionModal from './components/ConnectionModal';
import ProfitTracker from './components/ProfitTracker';
import DailyPNLCalendar from './components/DailyPNLCalendar';
import './index.css';

const API_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

function App() {
  // Connection state
  const [isConnected, setIsConnected] = useState(false);
  const [isBotRunning, setIsBotRunning] = useState(false);
  const [showConnectModal, setShowConnectModal] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showPNL, setShowPNL] = useState(false);

  // Data state
  const [account, setAccount] = useState(null);
  const [positions, setPositions] = useState([]);
  const [price, setPrice] = useState(null);
  const [reasoning, setReasoning] = useState([]);
  const [config, setConfig] = useState(null);

  // WebSocket
  const [ws, setWs] = useState(null);

  // Connect WebSocket
  const connectWebSocket = useCallback(() => {
    const socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      console.log('WebSocket connected');
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        switch (data.type) {
          case 'status':
            setIsBotRunning(data.data.bot_running);
            setIsConnected(data.data.mt5_connected);
            break;
          case 'account':
            setAccount(data.data);
            break;
          case 'positions':
            setPositions(data.data);
            break;
          case 'price':
            setPrice(data.data);
            break;
          case 'reasoning':
            // Deduplicate - check if same timestamp already exists
            setReasoning(prev => {
              const newItem = data.data;
              const isDuplicate = prev.some(
                item => item.timestamp === newItem.timestamp &&
                  item.symbol === newItem.symbol &&
                  item.type === newItem.type
              );
              if (isDuplicate) return prev;
              return [newItem, ...prev].slice(0, 50);
            });
            break;
          case 'trade':
            console.log('Trade executed:', data.data);
            break;
          case 'error':
            console.error('Bot error:', data.data.message);
            break;
        }
      } catch (e) {
        // Heartbeat or ping
        if (event.data === 'heartbeat') {
          socket.send('ping');
        }
      }
    };

    socket.onclose = () => {
      console.log('WebSocket disconnected');
      // Reconnect after 3 seconds
      setTimeout(connectWebSocket, 3000);
    };

    socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setWs(socket);
  }, []);

  // Fetch initial data
  const fetchInitialData = async () => {
    try {
      // Get status
      const statusRes = await fetch(`${API_URL}/api/status`);
      const status = await statusRes.json();
      setIsBotRunning(status.bot_running);
      setIsConnected(status.mt5_connected);

      if (status.mt5_connected) {
        // Get account
        const accountRes = await fetch(`${API_URL}/api/account`);
        const accountData = await accountRes.json();
        if (!accountData.error) setAccount(accountData);

        // Get positions
        const positionsRes = await fetch(`${API_URL}/api/positions`);
        const positionsData = await positionsRes.json();
        setPositions(positionsData);

        // Get price
        const priceRes = await fetch(`${API_URL}/api/price`);
        const priceData = await priceRes.json();
        if (!priceData.error) setPrice(priceData);
      }

      // Get config
      const configRes = await fetch(`${API_URL}/api/config`);
      const configData = await configRes.json();
      setConfig(configData);

      // Get reasoning history
      const reasoningRes = await fetch(`${API_URL}/api/reasoning`);
      const reasoningData = await reasoningRes.json();
      setReasoning(reasoningData.reverse());

    } catch (error) {
      console.error('Failed to fetch initial data:', error);
    }
  };

  // Initialize
  useEffect(() => {
    fetchInitialData();
    connectWebSocket();

    return () => {
      if (ws) ws.close();
    };
  }, []);

  // Handle MT5 connection
  const handleConnect = async (credentials) => {
    try {
      const res = await fetch(`${API_URL}/api/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(credentials)
      });
      const result = await res.json();

      if (result.success) {
        setIsConnected(true);
        setShowConnectModal(false);
        fetchInitialData();
      } else {
        alert(`Connection failed: ${result.error}`);
      }
    } catch (error) {
      alert(`Connection error: ${error.message}`);
    }
  };

  // Handle bot start/stop
  const handleToggleBot = async () => {
    try {
      const endpoint = isBotRunning ? '/api/stop' : '/api/start';
      const res = await fetch(`${API_URL}${endpoint}`, { method: 'POST' });
      const result = await res.json();

      if (result.success) {
        setIsBotRunning(!isBotRunning);
      } else {
        alert(`Failed: ${result.error}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    }
  };

  // Handle position close
  const handleClosePosition = async (ticket) => {
    try {
      const res = await fetch(`${API_URL}/api/positions/${ticket}/close`, {
        method: 'POST'
      });
      const result = await res.json();

      if (result.success) {
        setPositions(prev => prev.filter(p => p.ticket !== ticket));
      } else {
        alert(`Failed to close: ${result.error}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    }
  };

  // Handle position modify
  const handleModifyPosition = async (ticket, sl, tp) => {
    try {
      const res = await fetch(`${API_URL}/api/positions/${ticket}/modify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sl, tp })
      });
      const result = await res.json();

      if (!result.success) {
        alert(`Failed to modify: ${result.error}`);
      }
    } catch (error) {
      alert(`Error: ${error.message}`);
    }
  };

  // Handle config update
  const handleConfigUpdate = async (updates) => {
    try {
      const res = await fetch(`${API_URL}/api/config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      });
      const result = await res.json();
      setConfig(result);
    } catch (error) {
      console.error('Failed to update config:', error);
    }
  };

  return (
    <div className="app-container">
      {/* Header */}
      <header className="header">
        <div className="header-title">
          <div style={{
            width: '32px',
            height: '32px',
            background: 'linear-gradient(135deg, #00d46a, #00a854)',
            borderRadius: '8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: '700',
            fontSize: '0.8rem',
            color: '#000'
          }}>NX</div>
          <h1>NEXUS</h1>
          <span className={`status-badge ${isConnected ? 'connected' : 'disconnected'}`}>
            <span className={`status-dot ${isConnected ? 'connected' : 'disconnected'}`}></span>
            {isConnected ? 'LIVE' : 'OFFLINE'}
          </span>
        </div>

        <div className="header-controls">
          {!isConnected && (
            <button className="btn btn-primary" onClick={() => setShowConnectModal(true)}>
              Connect MT5
            </button>
          )}
          {isConnected && (
            <button
              className={`btn ${isBotRunning ? 'btn-danger' : 'btn-success'}`}
              onClick={handleToggleBot}
            >
              {isBotRunning ? 'Stop' : 'Start'}
            </button>
          )}
        </div>
      </header>

      {/* Dashboard Grid - 3 Columns */}
      <div className="dashboard-grid">
        {/* Left Sidebar */}
        <div className="sidebar-left">
          <StatusPanel
            account={account}
            price={price}
            isConnected={isConnected}
            isBotRunning={isBotRunning}
          />
          <ConfigPanel
            config={config}
            onUpdate={handleConfigUpdate}
          />
        </div>

        {/* Main Content */}
        <div className="main-content">
          <PositionsTable
            positions={positions}
            onClose={handleClosePosition}
            onModify={handleModifyPosition}
          />
          <AIReasoningFeed reasoning={reasoning} />
        </div>

        {/* Right Sidebar */}
        <div className="sidebar-right">
          <div className="card">
            <div className="card-header">
              <span className="card-title">Quick Actions</span>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <button
                className="btn btn-success"
                onClick={() => fetch(`${API_URL}/api/order`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ order_type: 'BUY' })
                })}
                disabled={!isConnected}
              >
                BUY
              </button>
              <button
                className="btn btn-danger"
                onClick={() => fetch(`${API_URL}/api/order`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ order_type: 'SELL' })
                })}
                disabled={!isConnected}
              >
                SELL
              </button>
              <button
                className="btn btn-outline"
                onClick={() => fetch(`${API_URL}/api/positions/close-all`, { method: 'POST' })}
                disabled={!isConnected || positions.length === 0}
              >
                Close All
              </button>
            </div>
          </div>

          {/* Session Stats */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Session Stats</span>
            </div>
            <div className="status-grid">
              <div className="status-item">
                <span className="status-label">Open Positions</span>
                <span className="status-value">{positions.length}</span>
              </div>
              <div className="status-item">
                <span className="status-label">Total P/L</span>
                <span className={`status-value ${positions.reduce((acc, p) => acc + p.profit, 0) >= 0 ? 'positive' : 'negative'}`}>
                  ${positions.reduce((acc, p) => acc + p.profit, 0).toFixed(2)}
                </span>
              </div>
              <div className="status-item">
                <span className="status-label">AI Signals</span>
                <span className="status-value">{reasoning.length}</span>
              </div>
            </div>
          </div>

          {/* Analytics */}
          <ProfitTracker />

          {/* Daily PNL */}
          <DailyPNLCalendar />
        </div>
      </div>

      {/* Connection Modal */}
      {showConnectModal && (
        <ConnectionModal
          onConnect={handleConnect}
          onClose={() => setShowConnectModal(false)}
        />
      )}
    </div>
  );
}

export default App;
