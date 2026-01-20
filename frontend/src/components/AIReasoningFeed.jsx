import { memo } from 'react';

const AIReasoningFeed = memo(function AIReasoningFeed({ reasoning }) {
    const formatTime = (timestamp) => {
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: false
            });
        } catch {
            return '--:--:--';
        }
    };

    const getDecisionClass = (decision) => {
        const d = decision?.toUpperCase();
        if (d === 'BUY') return 'buy';
        if (d === 'SELL') return 'sell';
        if (d === 'WAIT') return 'wait';
        if (d === 'HOLD') return 'hold';
        if (d === 'CLOSE') return 'sell';
        if (d === 'MODIFY_SL' || d === 'MODIFY_TP') return 'hold';
        return 'wait';
    };

    const getDecision = (item) => {
        if (item.result?.decision) return item.result.decision;
        if (item.result?.action) return item.result.action;
        return 'PROCESSING';
    };

    const getReason = (item) => {
        if (item.result?.reason) return item.result.reason;
        if (item.result?.Reason) return item.result.Reason;
        if (item.result?.error) return `Error: ${item.result.error}`;
        return 'Analyzing...';
    };

    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">AI Reasoning Feed</span>
                <span className="card-badge">LIVE</span>
            </div>

            {reasoning.length > 0 ? (
                <div className="reasoning-feed">
                    {reasoning.map((item, index) => (
                        <div
                            key={`${item.timestamp}-${index}`}
                            className={`reasoning-item ${item.type?.toLowerCase()}`}
                        >
                            <div className="reasoning-header">
                                <span className="reasoning-symbol">
                                    {item.symbol}
                                    {item.ticket && (
                                        <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginLeft: '0.5rem' }}>
                                            #{item.ticket}
                                        </span>
                                    )}
                                </span>
                                <span className="reasoning-time">
                                    {formatTime(item.timestamp)}
                                </span>
                            </div>

                            <div>
                                <span className={`reasoning-decision ${getDecisionClass(getDecision(item))}`}>
                                    {getDecision(item)}
                                </span>
                                {item.type && (
                                    <span style={{
                                        marginLeft: '0.5rem',
                                        fontSize: '0.7rem',
                                        color: 'var(--text-muted)',
                                        textTransform: 'uppercase'
                                    }}>
                                        {item.type}
                                    </span>
                                )}
                            </div>

                            <p className="reasoning-text">{getReason(item)}</p>

                            {/* Show trading details if available */}
                            {item.result?.decision && item.result.decision !== 'WAIT' && (
                                <div style={{
                                    marginTop: '0.5rem',
                                    padding: '0.5rem',
                                    background: 'rgba(0,0,0,0.2)',
                                    borderRadius: '0.25rem',
                                    fontSize: '0.75rem',
                                    color: 'var(--text-secondary)'
                                }}>
                                    {item.result.entry_price && (
                                        <div>📍 Entry: <strong>{item.result.entry_price}</strong></div>
                                    )}
                                    <div style={{ display: 'flex', gap: '1rem', marginTop: '0.25rem' }}>
                                        {item.result.SL && (
                                            <span style={{ color: 'var(--accent-red)' }}>
                                                SL: {item.result.SL} ({item.result.sl_pips || '?'} pips)
                                            </span>
                                        )}
                                        {item.result.TP && (
                                            <span style={{ color: 'var(--accent-green)' }}>
                                                TP: {item.result.TP} ({item.result.tp_pips || '?'} pips)
                                            </span>
                                        )}
                                    </div>
                                    {item.result.rr_ratio && (
                                        <div style={{ marginTop: '0.25rem' }}>
                                            R:R {item.result.rr_ratio} | Confidence: {item.result.confidence}%
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Show confidence for WAIT decisions */}
                            {item.result?.decision === 'WAIT' && item.result?.confidence !== undefined && (
                                <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                    Confidence: {item.result.confidence}%
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            ) : (
                <div className="empty-state">
                    <div className="empty-state-icon">🧠</div>
                    <p>No AI reasoning yet</p>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        Start the bot to see AI decisions
                    </p>
                </div>
            )}
        </div>
    );
});

export default AIReasoningFeed;
