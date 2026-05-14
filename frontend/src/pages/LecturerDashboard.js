import React, { useEffect, useState } from 'react';
import { getLecturerDashboard } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

export default function LecturerDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDay, setSelectedDay] = useState('');
  const { user, signOut } = useAuth();

  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const response = await getLecturerDashboard(selectedDay || null);
        setData(response.data);
      } catch (err) {
        setError(err.message || 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [selectedDay]);

  const handleDayFilter = (e) => {
    setSelectedDay(e.target.value);
  };

  return (
    <div className="page">
      <header>
        <h1>Lecturer Dashboard</h1>
        <button onClick={signOut}>Logout</button>
      </header>

      {loading && <p>Loading…</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {data && (
        <section>
          <h2>Welcome, {user?.first_name}</h2>

          <div style={{ marginBottom: '20px', padding: '10px', backgroundColor: '#f0f0f0', borderRadius: '5px' }}>
            <label htmlFor="day-filter" style={{ marginRight: '10px', fontWeight: 'bold' }}>
              Filter by Day:
            </label>
            <select
              id="day-filter"
              value={selectedDay}
              onChange={handleDayFilter}
              style={{
                padding: '8px 12px',
                borderRadius: '4px',
                border: '1px solid #ccc',
                fontSize: '14px',
                cursor: 'pointer',
              }}
            >
              <option value="">All Days</option>
              {days.map((day) => (
                <option key={day} value={day}>
                  {day}
                </option>
              ))}
            </select>
          </div>

          <h3>Courses</h3>
          <ul>
            {data.courses?.map((course) => (
              <li key={course.course_code}>
                {course.course_code}: {course.course_name}
              </li>
            ))}
          </ul>

          <h3>Upcoming Sessions</h3>
          <ul>
            {data.sessions?.length > 0 ? (
              data.sessions.map((session) => (
                <li key={session.id}>
                  {session.day_of_week} {session.start_time}-{session.end_time} - {session.course_code} ({session.room})
                </li>
              ))
            ) : (
              <li>No sessions scheduled {selectedDay ? `for ${selectedDay}` : ''}</li>
            )}
          </ul>
        </section>
      )}
    </div>
  );
}
