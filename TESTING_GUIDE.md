# Quick Reference: Testing the New Features

## API Endpoints

All endpoints are accessible at: `http://localhost:8000/api/reports/`

### 1. Attendance Report
```
GET /api/reports/attendance/
Filters: start_date, end_date, status, course_code, student_id, format
```

### 2. Enrollment Report
```
GET /api/reports/enrollment/
Filters: start_date, end_date, course_code, format
```

### 3. Course Attendance Summary
```
GET /api/reports/course-summary/
Filters: start_date, end_date, format
```

### 4. Student Performance Report
```
GET /api/reports/student-performance/
Filters: start_date, end_date, course_code, student_id, format
```

---

## Example API Calls

### Get JSON (Default)
```bash
curl http://localhost:8000/api/reports/attendance/
```

### Get CSV Export
```bash
curl http://localhost:8000/api/reports/attendance/?format=csv > attendance.csv
```

### Get PDF Export
```bash
curl http://localhost:8000/api/reports/attendance/?format=pdf > attendance.pdf
```

### Filter by Date Range
```bash
curl "http://localhost:8000/api/reports/attendance/?start_date=2024-05-01&end_date=2024-05-31"
```

### Filter by Status
```bash
curl "http://localhost:8000/api/reports/attendance/?status=Absent"
```

### Filter by Course
```bash
curl "http://localhost:8000/api/reports/attendance/?course_code=CS101"
```

### Multiple Filters
```bash
curl "http://localhost:8000/api/reports/attendance/?start_date=2024-05-01&status=Late&course_code=CS101&format=csv"
```

### Filter by Student (Admin/Lecturer only)
```bash
curl "http://localhost:8000/api/reports/attendance/?student_id=10"
```

---

## Expected Response (JSON)

```json
{
  "success": true,
  "message": "Attendance report retrieved successfully.",
  "data": {
    "count": 150,
    "start_date": "2024-05-01",
    "end_date": "2024-05-31",
    "records": [
      {
        "id": 1,
        "student_name": "John Doe",
        "student_id": 10,
        "course_code": "CS101",
        "course_name": "Introduction to Computer Science",
        "date": "2024-05-15",
        "time": "09:30",
        "status": "Present",
        "lecturer": "Dr. Jane Smith"
      }
    ]
  }
}
```

---

## Test Scenarios

### Scenario 1: Student Access
1. Login as a student
2. Call: `GET /api/reports/attendance/`
3. **Expected:** Only this student's records returned
4. Call: `GET /api/reports/enrollment/`
5. **Expected:** Permission denied error (403)

### Scenario 2: Lecturer Access
1. Login as a lecturer
2. Call: `GET /api/reports/course-summary/`
3. **Expected:** All courses with aggregated data
4. Call: `GET /api/reports/student-performance/`
5. **Expected:** Only students in this lecturer's classes

### Scenario 3: Admin Access
1. Login as admin
2. Call: `GET /api/reports/attendance/`
3. **Expected:** All attendance records
4. Call: `GET /api/reports/enrollment/?student_id=10`
5. **Expected:** All enrollments for student ID 10

### Scenario 4: Export Formats
1. Call: `GET /api/reports/attendance/?format=csv`
2. **Expected:** CSV file with proper headers
3. Call: `GET /api/reports/attendance/?format=pdf`
4. **Expected:** PDF file with formatted table

### Scenario 5: Date Filtering
1. Call: `GET /api/reports/attendance/`
2. **Expected:** Data from 1st of current month to today
3. Call: `GET /api/reports/attendance/?start_date=2024-03-01&end_date=2024-03-31`
4. **Expected:** Data only for March 2024

### Scenario 6: Status Filtering
1. Call: `GET /api/reports/attendance/?status=Absent`
2. **Expected:** Only records where status = "Absent"
3. Call: `GET /api/reports/attendance/?status=Present`
4. **Expected:** Only records where status = "Present"

---

## Admin Interface Enhancements

### Test Role Verification
1. Login as student
2. Try to access `/admin/` path
3. **Expected:** Redirected to student dashboard with error message
4. Login as admin
5. **Expected:** Can access admin interface

---

## CSV Export Format

### Attendance CSV Headers
```
Student Name, Student ID, Course Code, Course Name, Date, Time, Status, Lecturer
```

### Enrollment CSV Headers
```
Student Number, Student Name, Email, Course Code, Course Name, Modules, Enrollment Date
```

### Course Summary CSV Headers
```
Course Code, Course Name, Total Students, Total Sessions, Total Attendance Records, Attendance Rate (%), Present, Absent, Late
```

### Performance CSV Headers
```
Student Number, Student Name, Email, Total Sessions, Present, Absent, Late, Attendance Rate (%), Performance Score
```

---

## PDF Export Format

- Professional header with report title
- Date range displayed
- Data in formatted table
- Color-coded headers (blue background, white text)
- Limited to 40-50 records for readability
- Shows "(...more records)" if data exceeds limit

---

## Error Responses

### Unauthorized (Not Logged In)
```json
{
  "success": false,
  "message": "Unauthorized",
  "status_code": 401
}
```

### Insufficient Permissions
```json
{
  "success": false,
  "message": "Insufficient permissions",
  "status_code": 403
}
```

### Invalid Parameters
```json
{
  "success": false,
  "message": "Invalid date format"
}
```

---

## Performance Notes

- Attendance report: Handles 1000+ records efficiently
- PDF export limited to 50 records per page
- CSV export: Unlimited records
- Default date range reduces query size automatically
- User-specific filtering reduces query results

---

## Browser Testing

### Access Reports from Frontend
Add buttons to student/lecturer/admin dashboards:

```html
<!-- View Attendance Report -->
<a href="/api/reports/attendance/?format=json">View Report</a>

<!-- Download CSV -->
<a href="/api/reports/attendance/?format=csv" download>Download CSV</a>

<!-- Download PDF -->
<a href="/api/reports/attendance/?format=pdf" download>Download PDF</a>
```

---

## Troubleshooting

### Issue: 404 Not Found on report endpoints
**Solution:** Verify `api_urls.py` includes new endpoints and server is running

### Issue: Permission Denied (403)
**Solution:** Verify user role is correct (students can only access own data)

### Issue: PDF not opening
**Solution:** Verify reportlab is installed: `pip install reportlab`

### Issue: CSV file empty
**Solution:** Verify database has attendance records for date range

---

## Documentation References

- **Full API Docs:** See `REPORTS_API.md`
- **Rubric Mapping:** See `RUBRIC_IMPLEMENTATION.md`
- **Implementation Details:** See `IMPLEMENTATION_SUMMARY.md`
- **Code Documentation:** See `backend/report_views.py`
