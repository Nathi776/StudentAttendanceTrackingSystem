# Reports API Documentation

This document describes the new reporting features added to the Student Attendance Tracking System.

## Overview

The system now provides 4 comprehensive report APIs with filtering, aggregation, and export capabilities:

1. **Attendance Report** - Detailed attendance records
2. **Enrollment Report** - Student course enrollments
3. **Course Attendance Summary** - Aggregated statistics per course
4. **Student Performance Report** - Individual student analytics

## Endpoints

### 1. Attendance Report
**URL:** `/api/reports/attendance/`  
**Method:** `GET`  
**Authentication:** Required  
**Permission:** Students (own data), Lecturers (their classes), Admins (all)

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | YYYY-MM-DD | 1st of current month | Start date for report |
| `end_date` | YYYY-MM-DD | Today | End date for report |
| `status` | string | - | Filter by status: `Present`, `Absent`, or `Late` |
| `course_code` | string | - | Filter by specific course code |
| `student_id` | integer | - | Filter by student ID (admin/lecturer only) |
| `format` | string | `json` | Export format: `json`, `csv`, or `pdf` |

#### Example Requests

```bash
# Get attendance for current month in JSON
curl "http://localhost:8000/api/reports/attendance/"

# Get attendance for specific date range, CSV export
curl "http://localhost:8000/api/reports/attendance/?start_date=2024-05-01&end_date=2024-05-31&format=csv"

# Get only absent students, PDF export
curl "http://localhost:8000/api/reports/attendance/?status=Absent&format=pdf"

# Get attendance for specific course
curl "http://localhost:8000/api/reports/attendance/?course_code=CS101&format=csv"
```

#### Response (JSON)

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

### 2. Enrollment Report
**URL:** `/api/reports/enrollment/`  
**Method:** `GET`  
**Authentication:** Required  
**Permission:** Admins and Lecturers only

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `course_code` | string | - | Filter by specific course code |
| `start_date` | YYYY-MM-DD | - | Enrollment date range start |
| `end_date` | YYYY-MM-DD | - | Enrollment date range end |
| `format` | string | `json` | Export format: `json`, `csv`, or `pdf` |

#### Example Requests

```bash
# Get all enrollments
curl "http://localhost:8000/api/reports/enrollment/"

# Get enrollments for specific course
curl "http://localhost:8000/api/reports/enrollment/?course_code=CS101&format=csv"

# Get enrollments from last month
curl "http://localhost:8000/api/reports/enrollment/?start_date=2024-04-01&end_date=2024-04-30&format=pdf"
```

#### Response (JSON)

```json
{
  "success": true,
  "message": "Enrollment report retrieved successfully.",
  "data": {
    "count": 45,
    "records": [
      {
        "student_id": 10,
        "student_name": "John Doe",
        "student_number": "STU001",
        "email": "john@example.com",
        "course_code": "CS101",
        "course_name": "Introduction to Computer Science",
        "modules": "MOD001, MOD002",
        "enrollment_date": "2024-01-15"
      }
    ]
  }
}
```

---

### 3. Course Attendance Summary
**URL:** `/api/reports/course-summary/`  
**Method:** `GET`  
**Authentication:** Required  
**Permission:** Admins and Lecturers only

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | YYYY-MM-DD | 1st of current month | Period start |
| `end_date` | YYYY-MM-DD | Today | Period end |
| `format` | string | `json` | Export format: `json`, `csv`, or `pdf` |

#### Example Requests

```bash
# Get course attendance summary
curl "http://localhost:8000/api/reports/course-summary/"

# Export as CSV
curl "http://localhost:8000/api/reports/course-summary/?format=csv" > summary.csv

# Specific date range
curl "http://localhost:8000/api/reports/course-summary/?start_date=2024-05-01&end_date=2024-05-31&format=pdf"
```

#### Response (JSON)

```json
{
  "success": true,
  "message": "Course attendance summary retrieved successfully.",
  "data": {
    "count": 8,
    "start_date": "2024-05-01",
    "end_date": "2024-05-31",
    "records": [
      {
        "course_code": "CS101",
        "course_name": "Introduction to Computer Science",
        "total_students": 120,
        "total_sessions": 15,
        "total_attendance_records": 1650,
        "attendance_rate_percent": 85.5,
        "present": 1410,
        "absent": 180,
        "late": 60
      }
    ]
  }
}
```

---

### 4. Student Performance Report
**URL:** `/api/reports/student-performance/`  
**Method:** `GET`  
**Authentication:** Required  
**Permission:** All users (own data for students, filtered for lecturers, all for admins)

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `start_date` | YYYY-MM-DD | 1st of current month | Period start |
| `end_date` | YYYY-MM-DD | Today | Period end |
| `student_id` | integer | - | Filter by specific student (admin/lecturer only) |
| `course_code` | string | - | Filter by specific course |
| `format` | string | `json` | Export format: `json`, `csv`, or `pdf` |

#### Example Requests

```bash
# Get all students' performance (admin only)
curl "http://localhost:8000/api/reports/student-performance/"

# Get specific student's performance
curl "http://localhost:8000/api/reports/student-performance/?student_id=10"

# Get performance for specific course
curl "http://localhost:8000/api/reports/student-performance/?course_code=CS101&format=csv"

# Student sees their own performance
curl "http://localhost:8000/api/reports/student-performance/"
```

#### Response (JSON)

```json
{
  "success": true,
  "message": "Student performance report retrieved successfully.",
  "data": {
    "count": 120,
    "start_date": "2024-05-01",
    "end_date": "2024-05-31",
    "records": [
      {
        "student_id": 10,
        "student_name": "John Doe",
        "student_number": "STU001",
        "email": "john@example.com",
        "total_sessions": 45,
        "present": 42,
        "absent": 2,
        "late": 1,
        "attendance_rate_percent": 93.33,
        "performance_score": 93.33
      }
    ]
  }
}
```

---

## Export Formats

### JSON
- Default format
- Returns structured data with metadata
- Suitable for API integration

### CSV
- Filename format: `{report_type}_report.csv`
- Standard comma-separated values
- Importable to Excel/Sheets
- Suitable for data analysis

### PDF
- Filename format: `{report_type}_report.pdf`
- Formatted table layout
- Professional presentation
- Limited to first 40-50 records for readability

---

## Access Control

### Students
- Can only access their own attendance and performance data
- Cannot access other students' data
- Cannot access admin reports (enrollment, course summary)

### Lecturers
- Can access enrollment and course summary reports
- Can see attendance for their own classes only
- Can see performance for students in their classes

### Admins
- Full access to all reports
- Can filter by any student or course
- Can specify custom date ranges

---

## Date Range Defaults

If no date range is specified:
- **start_date**: First day of current month
- **end_date**: Today's date

Example: If today is May 15, 2024:
- Default range: May 1, 2024 to May 15, 2024

---

## Error Responses

### Insufficient Permissions
```json
{
  "success": false,
  "message": "Insufficient permissions",
  "status_code": 403
}
```

### Invalid Date Format
```json
{
  "success": false,
  "message": "Invalid date format",
  "errors": {
    "start_date": "Expected YYYY-MM-DD format"
  }
}
```

### Unauthorized (Not Logged In)
```json
{
  "success": false,
  "message": "Unauthorized",
  "status_code": 401
}
```

---

## Usage Examples

### Using in Frontend (React/JavaScript)

```javascript
// Fetch attendance report
async function getAttendanceReport() {
  const params = new URLSearchParams({
    start_date: '2024-05-01',
    end_date: '2024-05-31',
    status: 'Present',
    format: 'json'
  });
  
  const response = await fetch(`/api/reports/attendance/?${params}`, {
    method: 'GET',
    credentials: 'include'
  });
  
  if (response.ok) {
    const data = await response.json();
    console.log(data.data.records);
  }
}

// Download CSV report
function downloadAttendanceCSV() {
  const params = new URLSearchParams({
    format: 'csv'
  });
  
  window.location.href = `/api/reports/attendance/?${params}`;
}

// Download PDF report
function downloadPerformancePDF() {
  const params = new URLSearchParams({
    format: 'pdf',
    start_date: '2024-05-01',
    end_date: '2024-05-31'
  });
  
  window.location.href = `/api/reports/student-performance/?${params}`;
}
```

---

## Performance Considerations

- Reports can handle large datasets (100+ records)
- PDF export is limited to first 40-50 records for performance
- CSV export has no record limit
- JSON response includes metadata (count, date range)

---

## Future Enhancements

- [ ] Scheduled report generation
- [ ] Email delivery of reports
- [ ] Custom report builder
- [ ] Chart/visualization generation
- [ ] Advanced filtering options
