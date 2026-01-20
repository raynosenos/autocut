import { memo, useState, useEffect } from 'react';

const ConfigPanel = memo(function ConfigPanel({ config, onUpdate }) {
    const [localConfig, setLocalConfig] = useState(config || {});

    useEffect(() => {
        if (config) {
            setLocalConfig(config);
        }
    }, [config]);

    const handleChange = (key, value) => {
        setLocalConfig(prev => ({ ...prev, [key]: value }));
    };

    const handleSave = () => {
        onUpdate(localConfig);
    };

    const sessions = ['london', 'newyork', 'asia', 'sydney'];

    const toggleSession = (session) => {
        const current = localConfig.allowed_sessions || [];
        const updated = current.includes(session)
            ? current.filter(s => s !== session)
            : [...current, session];
        handleChange('allowed_sessions', updated);
    };

    if (!config) {
        return (
            <div className="card">
                <div className="card-header">
                    <span className="card-title">Configuration</span>
                </div>
                <div className="empty-state">
                    <p>Loading configuration...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">Configuration</span>
            </div>

            <div className="config-form">
                {/* Trading Settings */}
                <div className="config-row">
                    <div className="config-group">
                        <label className="config-label">Lot Size</label>
                        <input
                            type="number"
                            className="config-input"
                            value={localConfig.lot_size || 0.01}
                            onChange={(e) => handleChange('lot_size', parseFloat(e.target.value))}
                            step="0.01"
                            min="0.01"
                        />
                    </div>
                    <div className="config-group">
                        <label className="config-label">Max Positions</label>
                        <input
                            type="number"
                            className="config-input"
                            value={localConfig.max_positions || 3}
                            onChange={(e) => handleChange('max_positions', parseInt(e.target.value))}
                            min="1"
                            max="10"
                        />
                    </div>
                </div>

                <div className="config-row">
                    <div className="config-group">
                        <label className="config-label">Risk %</label>
                        <input
                            type="number"
                            className="config-input"
                            value={localConfig.risk_percent || 1}
                            onChange={(e) => handleChange('risk_percent', parseFloat(e.target.value))}
                            step="0.5"
                            min="0.5"
                            max="10"
                        />
                    </div>
                    <div className="config-group">
                        <label className="config-label">Min R:R</label>
                        <input
                            type="number"
                            className="config-input"
                            value={localConfig.min_rr_ratio || 1.5}
                            onChange={(e) => handleChange('min_rr_ratio', parseFloat(e.target.value))}
                            step="0.1"
                            min="1"
                        />
                    </div>
                </div>

                {/* Auto BEP */}
                <div className="toggle-group">
                    <span>Auto Break-Even</span>
                    <label className="toggle">
                        <input
                            type="checkbox"
                            checked={localConfig.auto_bep_enabled || false}
                            onChange={(e) => handleChange('auto_bep_enabled', e.target.checked)}
                        />
                        <span className="toggle-slider"></span>
                    </label>
                </div>

                {localConfig.auto_bep_enabled && (
                    <div className="config-group">
                        <label className="config-label">BEP Trigger (pips)</label>
                        <input
                            type="number"
                            className="config-input"
                            value={localConfig.auto_bep_pips || 5}
                            onChange={(e) => handleChange('auto_bep_pips', parseFloat(e.target.value))}
                            step="1"
                            min="1"
                        />
                    </div>
                )}

                {/* Trailing Stop */}
                <div className="toggle-group">
                    <span>Trailing Stop</span>
                    <label className="toggle">
                        <input
                            type="checkbox"
                            checked={localConfig.trailing_stop_enabled || false}
                            onChange={(e) => handleChange('trailing_stop_enabled', e.target.checked)}
                        />
                        <span className="toggle-slider"></span>
                    </label>
                </div>

                {localConfig.trailing_stop_enabled && (
                    <div className="config-group">
                        <label className="config-label">Trail Distance (pips)</label>
                        <input
                            type="number"
                            className="config-input"
                            value={localConfig.trailing_stop_pips || 10}
                            onChange={(e) => handleChange('trailing_stop_pips', parseFloat(e.target.value))}
                            step="1"
                            min="5"
                        />
                    </div>
                )}

                {/* Session Filter */}
                <div className="toggle-group">
                    <span>Session Filter</span>
                    <label className="toggle">
                        <input
                            type="checkbox"
                            checked={localConfig.session_filter_enabled || false}
                            onChange={(e) => handleChange('session_filter_enabled', e.target.checked)}
                        />
                        <span className="toggle-slider"></span>
                    </label>
                </div>

                {localConfig.session_filter_enabled && (
                    <div className="session-chips">
                        {sessions.map(session => (
                            <button
                                key={session}
                                className={`session-chip ${(localConfig.allowed_sessions || []).includes(session) ? 'active' : ''}`}
                                onClick={() => toggleSession(session)}
                            >
                                {session.charAt(0).toUpperCase() + session.slice(1)}
                            </button>
                        ))}
                    </div>
                )}

                {/* Save Button */}
                <button className="btn btn-primary" onClick={handleSave}>
                    Save Changes
                </button>
            </div>
        </div>
    );
});

export default ConfigPanel;
