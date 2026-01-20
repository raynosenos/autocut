import { memo, useState } from 'react';

const PositionsTable = memo(function PositionsTable({ positions, onClose, onModify }) {
    const [editingTicket, setEditingTicket] = useState(null);
    const [editSL, setEditSL] = useState('');
    const [editTP, setEditTP] = useState('');

    const handleEdit = (position) => {
        setEditingTicket(position.ticket);
        setEditSL(position.sl || '');
        setEditTP(position.tp || '');
    };

    const handleSave = (ticket) => {
        onModify(ticket, parseFloat(editSL) || null, parseFloat(editTP) || null);
        setEditingTicket(null);
    };

    const handleCancel = () => {
        setEditingTicket(null);
        setEditSL('');
        setEditTP('');
    };

    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">Active Positions</span>
                <span className="card-badge">{positions.length}</span>
            </div>

            {positions.length > 0 ? (
                <table className="positions-table">
                    <thead>
                        <tr>
                            <th>Symbol</th>
                            <th>Type</th>
                            <th>Volume</th>
                            <th>Open Price</th>
                            <th>SL</th>
                            <th>TP</th>
                            <th>Profit</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {positions.map((position) => (
                            <tr key={position.ticket} className="fade-in">
                                <td>
                                    <strong>{position.symbol}</strong>
                                    <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                                        #{position.ticket}
                                    </div>
                                </td>
                                <td>
                                    <span className={`position-type ${position.type.toLowerCase()}`}>
                                        {position.type}
                                    </span>
                                </td>
                                <td>{position.volume}</td>
                                <td>{position.open_price?.toFixed(2)}</td>
                                <td>
                                    {editingTicket === position.ticket ? (
                                        <input
                                            type="number"
                                            className="config-input"
                                            value={editSL}
                                            onChange={(e) => setEditSL(e.target.value)}
                                            style={{ width: '80px', padding: '0.25rem' }}
                                            step="0.01"
                                        />
                                    ) : (
                                        position.sl?.toFixed(2) || '-'
                                    )}
                                </td>
                                <td>
                                    {editingTicket === position.ticket ? (
                                        <input
                                            type="number"
                                            className="config-input"
                                            value={editTP}
                                            onChange={(e) => setEditTP(e.target.value)}
                                            style={{ width: '80px', padding: '0.25rem' }}
                                            step="0.01"
                                        />
                                    ) : (
                                        position.tp?.toFixed(2) || '-'
                                    )}
                                </td>
                                <td>
                                    <span className={position.profit >= 0 ? 'status-value positive' : 'status-value negative'}>
                                        {position.profit >= 0 ? '+' : ''}${position.profit?.toFixed(2)}
                                    </span>
                                </td>
                                <td>
                                    <div className="position-actions">
                                        {editingTicket === position.ticket ? (
                                            <>
                                                <button
                                                    className="btn btn-success"
                                                    onClick={() => handleSave(position.ticket)}
                                                >
                                                    Save
                                                </button>
                                                <button
                                                    className="btn btn-outline"
                                                    onClick={handleCancel}
                                                >
                                                    Cancel
                                                </button>
                                            </>
                                        ) : (
                                            <>
                                                <button
                                                    className="btn btn-primary"
                                                    onClick={() => handleEdit(position)}
                                                >
                                                    Edit
                                                </button>
                                                <button
                                                    className="btn btn-danger"
                                                    onClick={() => onClose(position.ticket)}
                                                >
                                                    Close
                                                </button>
                                            </>
                                        )}
                                    </div>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            ) : (
                <div className="empty-state">
                    <div className="empty-state-icon">--</div>
                    <p>No open positions</p>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                        Start the bot or place a manual trade
                    </p>
                </div>
            )}
        </div>
    );
});

export default PositionsTable;
