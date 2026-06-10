# AI Documentation

This document explains the AI-related features in the Student Attendance Tracking System, how they work, and how to extend them safely.

## Overview

The project uses two AI-assisted capabilities:

1. A rule-based chatbot for students and lecturers.
2. Face recognition for student face enrollment and attendance marking.

The AI features are implemented in the Django backend and are exposed through the dashboard UI and JSON API endpoints.

## AI Architecture

The AI layer is intentionally lightweight and deterministic:

- The chatbot does not use a large language model.
- Intent matching is handled by a custom scorer built on phrases, keywords, token overlap, role-specific rules, and priority weighting.
- Face recognition uses `face_recognition` and `dlib` to detect a face, generate a 128-dimensional embedding, and compare embeddings.
- Attendance is only written after the student identity is verified and the student is allowed to attend the selected session.

This approach keeps the system explainable, easier to debug, and suitable for an academic attendance workflow.

## Chatbot

### Purpose

The chatbot answers natural-language questions about attendance, enrolment, lecturers, exams, and session information.

### Main Files

- [backend/webapp/chat_intents.py](../backend/webapp/chat_intents.py)
- [backend/webapp/views.py](../backend/webapp/views.py)
- [backend/webapp/templates/includes/ai_chat.html](../backend/webapp/templates/includes/ai_chat.html)

### How It Works

1. The user types a question in the chat widget.
2. The frontend sends the message to the Django `ai_chat` endpoint.
3. `resolve_chat_intent()` normalizes the message and scores each intent.
4. The best matching intent is selected based on score and priority.
5. `ai_chat()` builds the response from attendance and enrolment data.

### Intent Matching Rules

Intent detection uses the following signals:

- Example phrase similarity.
- Keyword overlap.
- Token overlap.
- Role restrictions, such as student-only or lecturer-only intents.
- Intent-specific bonuses or penalties.
- Priority tie-breaking.

### Lecturer Chatbot Capabilities

The lecturer assistant can answer questions about:

- Today’s attendance summary.
- Students with the most absences.
- Students who qualify for exams.
- Modules with the highest or lowest attendance.
- Attendance statistics for a specific module.
- Best attended class.
- Taught modules.

### Student Chatbot Capabilities

The student assistant can answer questions about:

- Next session.
- Absence count.
- Present count.
- Late count.
- Attendance percentage.
- Attendance summary.
- Attendance by module.
- Lowest and highest attendance module.
- Missed classes this week.
- Enrolled courses.
- Lecturer for a course.
- Attendance on a specific date.

### Important Notes

- The chatbot is rule-based, not generative.
- If a question is too vague, the bot falls back to a low-confidence reply.
- The system prefers predictable outputs over open-ended conversation.

## Face Recognition

### Purpose

Face recognition is used for two steps:

1. Face enrollment for a student.
2. Face verification when marking attendance.

### Main Files

- [backend/webapp/face_engine.py](../backend/webapp/face_engine.py)
- [backend/webapp/views.py](../backend/webapp/views.py)

### How It Works

1. The browser captures a webcam image.
2. The image is sent to Django as base64 JSON.
3. `encode_single_face()` detects exactly one face and creates an embedding.
4. For enrollment, the embedding is saved to `FaceEncoding`.
5. For attendance, the embedding is compared with the logged-in student’s stored encoding.
6. If the face match succeeds, attendance is recorded.

### Face Engine Details

The helper in `face_engine.py` provides:

- `encode_single_face(rgb_image)`
- `match_face(encoding, known_encodings, known_student_ids, threshold)`

`encode_single_face()` returns one of three statuses:

- `OK`
- `NO_FACE`
- `MULTIPLE_FACES`

`match_face()` returns:

- `MATCH`
- `UNKNOWN`
- `NO_KNOWN_FACES`

### Duplicate Face Protection

The face enrollment endpoint blocks duplicate faces across different student accounts by comparing new encodings against existing ones with a stricter threshold.

## Attendance Automation

### Student Attendance Flow

The attendance flow is controlled by [backend/webapp/views.py](../backend/webapp/views.py):

1. The student opens the dashboard.
2. The frontend checks whether an eligible class session is active.
3. If a session is active, the camera modal opens.
4. The student captures an image.
5. The backend validates:
   - session ID
   - module/course enrolment
   - lecturer match
   - face enrollment
   - face identity
6. Attendance is stored as `Present`, `Late`, or `Absent`.

### API Endpoints

- `POST /api/enroll-face/`
- `POST /api/mark-attendance/`

### Attendance Validation Rules

Attendance is only accepted when:

- The student is enrolled in the relevant course or module.
- The session belongs to the correct lecturer.
- The captured face matches the enrolled face.
- The image contains exactly one face.

### Time Handling

Attendance timestamps use the configured local timezone (`Africa/Johannesburg`) and are converted with `timezone.localtime()` for display and reporting.

## Frontend AI UI

### Chat Widget

The reusable chat widget lives in [backend/webapp/templates/includes/ai_chat.html](../backend/webapp/templates/includes/ai_chat.html).

It provides:

- A floating chat button.
- A message panel.
- A message input form.
- CSRF-protected requests to the chatbot endpoint.

### Student Dashboard Camera Modal

The student dashboard template includes:

- A camera modal.
- Webcam access through `navigator.mediaDevices.getUserMedia()`.
- Capture and submit controls.
- Error handling for no face, multiple faces, and network problems.

## Environment Variables

The AI features depend on the following backend settings and packages:

### Face Recognition

No dedicated environment variable is required for face recognition, but the server must have the native dependencies needed by `face_recognition` and `dlib`.

### Chatbot / Attendance

The chatbot and attendance features use the normal Django runtime, database, and session/auth settings.

### Email for Announcements

The project also supports transactional email for lecturer announcements:

- `SENDGRID_API_KEY`
- `SENDGRID_FROM_EMAIL`
- `DEFAULT_FROM_EMAIL`
- `EMAIL_TIMEOUT`

These are not part of the AI stack itself, but they are used by the lecturer workflow that often sits alongside attendance communication.

## Deployment Notes

### Railway

For Railway, make sure the backend image includes the system packages required by the face recognition stack. The project already includes deployment support files for this.

### Browser Requirements

Camera-based attendance requires:

- A secure context (`https://` in production, or `localhost` during development).
- Browser permission for camera access.
- A device with a working webcam.

## Extending The AI Layer

### Adding A New Chat Intent

To add a new chatbot capability:

1. Add a new `IntentDefinition` in [backend/webapp/chat_intents.py](../backend/webapp/chat_intents.py).
2. Add the response logic inside `ai_chat()` in [backend/webapp/views.py](../backend/webapp/views.py).
3. Add one or more example phrases and keywords.
4. Test the intent against existing ones to avoid collisions.

### Adding A New Face Workflow

If you want to extend the face pipeline:

1. Keep all face encoding and matching inside `face_engine.py`.
2. Reuse the same 128-dimensional embedding format.
3. Keep the verification step strict so attendance cannot be spoofed.

## Troubleshooting

### Chatbot Returns The Wrong Intent

Likely causes:

- Another intent has a stronger phrase match.
- The message is too short or too vague.
- The role does not match the intent.

Fix:

- Add a better example phrase.
- Add a stronger keyword signal.
- Adjust priority or intent-specific scoring.

### Camera Does Not Open

Likely causes:

- The browser blocked camera permissions.
- The device has no webcam.
- The modal opens, but `getUserMedia()` fails.

Fix:

- Check browser permissions.
- Open the dashboard in a secure context.
- Review the browser console for camera errors.

### Attendance Not Recorded

Likely causes:

- No session selected.
- Face not enrolled.
- Multiple faces detected.
- Face match failed.
- The student is not enrolled in the session’s course/module.

## Summary

The project’s AI layer is practical and focused:

- The chatbot is deterministic and role-aware.
- The face system is used for identity verification.
- Attendance is written only after the student is validated against the active session.

This keeps the system explainable, testable, and appropriate for an attendance-tracking application.