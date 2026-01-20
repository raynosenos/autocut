import { useState } from 'react';

function ConnectionModal({ onConnect, onClose }) {
    const [login, setLogin] = useState('');
    const [password, setPassword] = useState('');
    const [server, setServer] = useState('MetaQuotes-Demo');
    const [isConnecting, setIsConnecting] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();

        if (!login || !password || !server) {
            alert('Please fill in all fields');
            return;
        }

        setIsConnecting(true);

        try {
            await onConnect({
                login: parseInt(login),
                password,
                server
            });
        } finally {
            setIsConnecting(false);
        }
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal" onClick={e => e.stopPropagation()}>
                <h2 className="modal-title">🔗 Connect to MetaTrader 5</h2>

                <form onSubmit={handleSubmit}>
                    <div className="config-form">
                        <div className="config-group">
                            <label className="config-label">Login (Account Number)</label>
                            <input
                                type="number"
                                className="config-input"
                                placeholder="12345678"
                                value={login}
                                onChange={(e) => setLogin(e.target.value)}
                                required
                            />
                        </div>

                        <div className="config-group">
                            <label className="config-label">Password</label>
                            <input
                                type="password"
                                className="config-input"
                                placeholder="Your MT5 password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                            />
                        </div>

                        <div className="config-group">
                            <label className="config-label">Server</label>
                            <input
                                type="text"
                                className="config-input"
                                placeholder="MetaQuotes-Demo"
                                value={server}
                                onChange={(e) => setServer(e.target.value)}
                                required
                            />
                        </div>

                        <div style={{
                            padding: '0.75rem',
                            background: 'rgba(59, 130, 246, 0.1)',
                            borderRadius: '0.5rem',
                            fontSize: '0.8rem',
                            color: 'var(--text-secondary)'
                        }}>
                            💡 <strong>Tip:</strong> Use a demo account for testing.
                            Make sure MT5 terminal is running on this PC.
                        </div>

                        <div className="modal-actions">
                            <button
                                type="button"
                                className="btn btn-outline"
                                onClick={onClose}
                                disabled={isConnecting}
                            >
                                Cancel
                            </button>
                            <button
                                type="submit"
                                className="btn btn-primary"
                                disabled={isConnecting}
                            >
                                {isConnecting ? 'Connecting...' : 'Connect'}
                            </button>
                        </div>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default ConnectionModal;
