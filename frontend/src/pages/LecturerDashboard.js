import React, { useEffect, useState } from 'react';
import { getLecturerDashboard } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

function formatDateTime(isoString) {
  const date = new Date(isoString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

export default function LecturerDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedDay, setSelectedDay] = useState('');
  const { user, signOut } = useAuth();

  const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

  useEffect(() => {
    let intervalId;

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
    intervalId = window.setInterval(load, 30000);

    return () => {
      window.clearInterval(intervalId);
    };
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

          <h3>Recent Attendance</h3>
          <ul>
            {data.attendance_records?.length > 0 ? (
              data.attendance_records.map((record) => (
                <li key={record.id}>
                  {formatDateTime(record.date_time)}: {record.student_first_name} {record.student_last_name} - {record.course_code} - {record.status}
                </li>
              ))
            ) : (
              <li>No attendance records yet</li>
            )}
          </ul>
        </section>
      )}
    </div>
  );
}
