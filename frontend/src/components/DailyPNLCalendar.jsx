import { useState, useEffect } from 'react';

const API_URL = 'http://localhost:8000';

function DailyPNLCalendar() {
    const [currentDate, setCurrentDate] = useState(new Date());
    const [pnlData, setPnlData] = useState({});
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchPNLData();
    }, [currentDate]);

    const fetchPNLData = async () => {
        try {
            const res = await fetch(`${API_URL}/api/profit/stats`);
            const data = await res.json();

            const pnlMap = {};
            if (data.history) {
                data.history.forEach(day => {
                    pnlMap[day.date] = day.profit_day || 0;
                });
            }
            setPnlData(pnlMap);
            setLoading(false);
        } catch (error) {
            console.error('Failed to fetch PNL data:', error);
            setLoading(false);
        }
    };

    const getDaysInMonth = (year, month) => new Date(year, month + 1, 0).getDate();
    const getFirstDayOfMonth = (year, month) => new Date(year, month, 1).getDay();
    const formatDate = (year, month, day) => `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;

    const prevMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1));
    const nextMonth = () => setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1));

    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    const daysInMonth = getDaysInMonth(year, month);
    const firstDay = getFirstDayOfMonth(year, month);
    const monthStr = `${year}-${String(month + 1).padStart(2, '0')}`;

    const days = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

    const cells = [];
    for (let i = 0; i < firstDay; i++) cells.push({ day: null, pnl: null });
    for (let day = 1; day <= daysInMonth; day++) {
        const dateStr = formatDate(year, month, day);
        cells.push({ day, pnl: pnlData[dateStr] || 0, date: dateStr });
    }

    const getCellStyle = (pnl) => {
        if (pnl === null || pnl === 0) return { background: 'var(--bg-secondary)' };
        if (pnl > 0) return { background: 'rgba(0, 212, 106, 0.3)' };
        return { background: 'rgba(255, 71, 87, 0.3)' };
    };

    if (loading) {
        return (
            <div className="card">
                <div className="card-header">
                    <span className="card-title">Daily PNL</span>
                </div>
                <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--text-muted)' }}>
                    Loading...
                </div>
            </div>
        );
    }

    return (
        <div className="card">
            <div className="card-header">
                <span className="card-title">Daily PNL</span>
            </div>

            {/* Month Navigation */}
            <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '16px',
                marginBottom: '12px'
            }}>
                <button
                    onClick={prevMonth}
                    style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer',
                        fontSize: '1rem',
                        padding: '4px 8px'
                    }}
                >
                    ‹
                </button>
                <span style={{ fontWeight: '500', fontSize: '0.85rem' }}>{monthStr}</span>
                <button
                    onClick={nextMonth}
                    style={{
                        background: 'none',
                        border: 'none',
                        color: 'var(--text-secondary)',
                        cursor: 'pointer',
                        fontSize: '1rem',
                        padding: '4px 8px'
                    }}
                >
                    ›
                </button>
            </div>

            {/* Weekday Headers */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(7, 1fr)',
                gap: '3px',
                marginBottom: '6px'
            }}>
                {days.map((day, i) => (
                    <div key={i} style={{
                        textAlign: 'center',
                        fontSize: '0.65rem',
                        color: 'var(--text-muted)',
                        padding: '4px 0'
                    }}>
                        {day}
                    </div>
                ))}
            </div>

            {/* Calendar Grid */}
            <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(7, 1fr)',
                gap: '3px'
            }}>
                {cells.map((cell, i) => (
                    <div
                        key={i}
                        style={{
                            ...getCellStyle(cell.pnl),
                            borderRadius: '4px',
                            padding: '6px 2px',
                            textAlign: 'center',
                            minHeight: '40px',
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'center'
                        }}
                    >
                        {cell.day && (
                            <>
                                <div style={{ fontSize: '0.75rem', fontWeight: '500' }}>
                                    {cell.day}
                                </div>
                                <div style={{
                                    fontSize: '0.55rem',
                                    color: cell.pnl > 0 ? 'var(--accent-green)' :
                                        cell.pnl < 0 ? 'var(--accent-red)' :
                                            'var(--text-muted)',
                                    marginTop: '1px'
                                }}>
                                    {cell.pnl !== 0 ? (cell.pnl > 0 ? '+' : '') + cell.pnl.toFixed(2) : '0.00'}
                                </div>
                            </>
                        )}
                    </div>
                ))}
            </div>
        </div>
    );
}

export default DailyPNLCalendar;
