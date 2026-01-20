import { useState, useEffect } from 'react';

const API_URL = 'http://localhost:8000';

function ProfitTracker() {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchStats();
        const interval = setInterval(fetchStats, 30000);
        return () => clearInterval(interval);
    }, []);

    const fetchStats = async () => {
        try {
            const res = await fetch(`${API_URL}/api/profit/stats`);
            const data = await res.json();
            setStats(data);
            setLoading(false);
        } catch (error) {
            console.error('Failed to fetch profit stats:', error);
            setLoading(false);
        }
    };

    if (loading || !stats) {
        return (
            <div className="card">
                <div className="card-header">
                    <span className="card-title">Performance</span>
                </div>
                <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    {loading ? 'Loading...' : 'No data'}
                </div>
            </div>
        );
    }

    const isPositive = stats.total_profit >= 0;
    const winRate = stats.win_rate || 0;

    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">Analytics</span>
                <span className="card-badge" style={{
                    background: isPositive ? 'var(--accent-green)' : 'var(--accent-red)',
                    color: isPositive ? '#000' : '#fff'
                }}>
                    {isPositive ? 'PROFIT' : 'LOSS'}
                </span>
            </div>

            {/* Balance Row */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: '1fr 1fr',
                gap: '12px',
                marginBottom: '16px'
            }}>
                <div style={{
                    background: 'var(--bg-secondary)',
                    padding: '14px',
                    borderRadius: '8px',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                        INITIAL
                    </div>
                    <div style={{ fontSize: '1rem', fontWeight: '600' }}>
                        ${stats.initial_balance?.toFixed(2) || '0.00'}
                    </div>
                </div>
                <div style={{
                    background: 'var(--bg-secondary)',
                    padding: '14px',
                    borderRadius: '8px',
                    textAlign: 'center'
                }}>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                        CURRENT
                    </div>
                    <div style={{ fontSize: '1rem', fontWeight: '600' }}>
                        ${stats.current_balance?.toFixed(2) || '0.00'}
                    </div>
                </div>
            </div>

            {/* Total Profit */}
            <div style={{
                background: isPositive ? 'rgba(0, 212, 106, 0.08)' : 'rgba(255, 71, 87, 0.08)',
                borderRadius: '10px',
                padding: '20px',
                textAlign: 'center',
                marginBottom: '16px'
            }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    TOTAL P&L
                </div>
                <div style={{
                    fontSize: '1.75rem',
                    fontWeight: '600',
                    color: isPositive ? 'var(--accent-green)' : 'var(--accent-red)'
                }}>
                    {isPositive ? '+' : ''}${stats.total_profit?.toFixed(2)}
                </div>
                <div style={{
                    fontSize: '0.85rem',
                    color: isPositive ? 'var(--accent-green)' : 'var(--accent-red)',
                    opacity: 0.8
                }}>
                    {isPositive ? '+' : ''}{stats.total_profit_percent?.toFixed(1)}%
                </div>
            </div>

            {/* Win Rate */}
            <div style={{
                background: 'var(--bg-secondary)',
                borderRadius: '10px',
                padding: '16px',
                textAlign: 'center',
                marginBottom: '16px'
            }}>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    WIN RATE
                </div>
                <div style={{
                    fontSize: '1.5rem',
                    fontWeight: '600',
                    color: winRate >= 50 ? 'var(--accent-green)' : 'var(--accent-red)'
                }}>
                    {winRate}%
                </div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    <span style={{ color: 'var(--accent-green)' }}>{stats.total_wins || 0}W</span>
                    <span style={{ margin: '0 6px' }}>·</span>
                    <span style={{ color: 'var(--accent-red)' }}>{stats.total_losses || 0}L</span>
                    <span style={{ margin: '0 6px' }}>·</span>
                    <span>{stats.total_trades || 0} trades</span>
                </div>
            </div>

            {/* Period Stats */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '8px'
            }}>
                {[
                    { label: 'Today', value: stats.today_profit },
                    { label: 'Week', value: stats.week_profit },
                    { label: 'Month', value: stats.month_profit }
                ].map(item => (
                    <div key={item.label} style={{
                        textAlign: 'center',
                        padding: '10px 8px',
                        background: 'var(--bg-secondary)',
                        borderRadius: '6px'
                    }}>
                        <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>
                            {item.label.toUpperCase()}
                        </div>
                        <div style={{
                            fontSize: '0.85rem',
                            fontWeight: '600',
                            color: item.value >= 0 ? 'var(--accent-green)' : 'var(--accent-red)',
                            marginTop: '2px'
                        }}>
                            {item.value >= 0 ? '+' : ''}${item.value?.toFixed(2)}
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

export default ProfitTracker;
