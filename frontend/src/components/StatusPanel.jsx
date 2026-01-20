import { memo } from 'react';

const StatusPanel = memo(function StatusPanel({ account, price, isConnected, isBotRunning }) {
    return (
        <>
            {/* Connection Status Card */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">MT5 Status</span>
                    <span className={`card-badge ${isConnected ? '' : 'style="background: var(--accent-red)"'}`}>
                        {isConnected ? 'ONLINE' : 'OFFLINE'}
                    </span>
                </div>

                <div className="status-grid">
                    <div className="status-item">
                        <span className="status-label">Status</span>
                        <span className={`status-value ${isConnected ? 'positive' : 'negative'}`}>
                            {isConnected ? '● Connected' : '○ Disconnected'}
                        </span>
                    </div>

                    <div className="status-item">
                        <span className="status-label">Bot</span>
                        <span className={`status-value ${isBotRunning ? 'positive' : ''}`}>
                            {isBotRunning ? '● Active' : '○ Stopped'}
                        </span>
                    </div>

                    <div className="status-item">
                        <span className="status-label">Market</span>
                        <span className="status-value">
                            {isConnected ? '● Open' : '○ Closed'}
                        </span>
                    </div>
                </div>
            </div>

            {/* Account Info Card */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">Account</span>
                </div>

                {account ? (
                    <div className="status-grid">
                        <div className="status-item">
                            <span className="status-label">Balance</span>
                            <span className="status-value">${account.balance?.toLocaleString()}</span>
                        </div>

                        <div className="status-item">
                            <span className="status-label">Equity</span>
                            <span className={`status-value ${account.equity >= account.balance ? 'positive' : 'negative'}`}>
                                ${account.equity?.toLocaleString()}
                            </span>
                        </div>

                        <div className="status-item">
                            <span className="status-label">Profit</span>
                            <span className={`status-value ${account.profit >= 0 ? 'positive' : 'negative'}`}>
                                {account.profit >= 0 ? '+' : ''}${account.profit?.toFixed(2)}
                            </span>
                        </div>

                        <div className="status-item">
                            <span className="status-label">Margin Level</span>
                            <span className="status-value">{account.margin_level?.toFixed(0)}%</span>
                        </div>

                        <div className="status-item">
                            <span className="status-label">Leverage</span>
                            <span className="status-value">1:{account.leverage}</span>
                        </div>
                    </div>
                ) : (
                    <div className="empty-state">
                        <p>Connect to MT5 to view account info</p>
                    </div>
                )}
            </div>

            {/* Price Card */}
            <div className="card">
                <div className="card-header">
                    <span className="card-title">{price?.symbol || 'XAUUSD'}</span>
                    <span className="card-badge">LIVE</span>
                </div>

                {price ? (
                    <div style={{
                        textAlign: 'center',
                        padding: '12px',
                        background: 'var(--bg-secondary)',
                        borderRadius: '8px'
                    }}>
                        <div style={{
                            fontSize: '1.1rem',
                            fontWeight: '600',
                            display: 'flex',
                            justifyContent: 'center',
                            alignItems: 'center',
                            gap: '8px'
                        }}>
                            <span style={{ color: 'var(--accent-green)' }}>{price.bid?.toFixed(2)}</span>
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>/</span>
                            <span style={{ color: 'var(--accent-red)' }}>{price.ask?.toFixed(2)}</span>
                        </div>
                        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                            Spread: {price.spread} pts
                        </div>
                    </div>
                ) : (
                    <div className="empty-state">
                        <p>---.--</p>
                    </div>
                )}
            </div>
        </>
    );
});

export default StatusPanel;
