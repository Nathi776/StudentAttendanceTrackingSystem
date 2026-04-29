import React, { useEffect, useState } from 'react';
import { getStudentDashboard } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import ThemeToggle from '../components/ThemeToggle';
import AIChatBox from '../components/AIChatBox';

export default function StudentDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const { user, signOut } = useAuth();

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const response = await getStudentDashboard();
        setData(response.data);
      } catch (err) {
        setError(err.message || 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, []);

  return (
    <div className="page">
      <ThemeToggle />
      <header>
        <h1>Student Dashboard</h1>
        <button onClick={signOut}>Logout</button>
      </header>

      {loading && <p>Loading…</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {data && (
        <section>
          <h2>Welcome, {user?.first_name}</h2>

          <h3>Next Coming Session</h3>
          {data.next_session ? (
            <div style={{ padding: '10px', border: '1px solid #ccc', borderRadius: '5px', backgroundColor: '#f9f9f9' }}>
              <p><strong>{data.next_session.course_code}</strong>: {data.next_session.course_name}</p>
              <p><strong>Day:</strong> {data.next_session.day_of_week}</p>
              <p><strong>Time:</strong> {data.next_session.start_time} - {data.next_session.end_time}</p>
              <p><strong>Room:</strong> {data.next_session.room}</p>
              <p><strong>Lecturer:</strong> {data.next_session.lecturer}</p>
            </div>
          ) : (
            <p>No upcoming sessions</p>
          )}

          <h3>Courses</h3>
          <ul>
            {data.subjects?.map((subject) => (
              <li key={subject.course_code}>
                {subject.course_code}: {subject.course_name} (Lecturer: {subject.lecturer_name})
              </li>
            ))}
          </ul>

          <h3>Attendance Records</h3>
          <ul>
            {data.attendance_records?.map((record, idx) => (
              <li key={idx}>
                {record.date_time}: {record.course_code} - {record.status}
              </li>
            ))}
          </ul>

          <h3>Upcoming Sessions</h3>
          <ul>
            {data.class_schedule?.map((session) => (
              <li key={session.id}>
                {session.day_of_week} {session.start_time}-{session.end_time} - {session.course_code} ({session.room})
              </li>
            ))}
          </ul>
        </section>
      )}

      {user?.user_type === 'Student' && <AIChatBox />}
    </div>
  );
}
