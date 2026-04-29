# Student Attendance Dashboard

A Java Swing desktop application for managing student attendance with smart analytics, auto-generated calendar visualization, and role-based dashboards (Student & Teacher).

---

## 🚀 How To Run

Compile all Java files:

```
javac *.java
```

Run the application:

```
java Main
```

Data is stored in:

```
attendance_data.ser
```

---

## ✨ Key Features

- Student & Teacher authentication
- Student dashboard with analytics
- Profile management
- Subject-wise attendance tracking
- Smart calendar (auto-generated attendance)
- Teacher dashboard with CSV export
- Real-time UI updates using listeners
- File-based persistence using serialization

---

## 🧠 Smart Calendar System (Auto Attendance)

The calendar does **NOT** require manual marking.

Instead, it automatically computes attendance using:
- Session start date
- Subject-wise attended classes

### Logic:
- Classes are distributed sequentially from session start
- Daily status is computed:

| Condition | Result |
|----------|--------|
| All subjects attended | Present (Green) |
| Any subject missed | Absent (Red) |
| No classes | No Class (Gray) |

### Benefit:
- No repetitive input
- Accurate visualization
- Data consistency

---

## 🔁 Navigation System (CardLayout)

The UI uses:

```
CardLayout
```

Instead of multiple windows, all pages are switched inside a single frame.

### Pages:
- Dashboard
- Attendance
- Profile

### Benefits:
- No overlapping windows
- Smooth transitions
- Better UX

---

## 📜 Scroll Management System

Fixes implemented:
- Removed duplicate scrollbars
- Prevented nested JScrollPane
- Ensured scroll works in fullscreen
- Only ONE scroll per content area

### Rule:
> One scroll controls everything.

---

## 🧱 Layout Strategy

Uses:
- BoxLayout (vertical stacking)
- GridBagLayout (flexible alignment)
- BorderLayout (main structure)

Avoids:
- Absolute positioning
- Component overlap issues

---

## 📊 Attendance Visualization

Dashboard includes:
- Attendance bar graph
- 75% threshold indicator
- Stats:
  - Attended classes
  - Absent classes
  - Percentage

---

## 🔔 Attendance Status Logic

| Percentage | Status |
|-----------|--------|
| ≥ 75% | SAFE |
| 60–74% | WARNING |
| < 60% | CRITICAL |

---

## 🧮 Algorithms Used (DAA Concepts)

### 1. Greedy Logic
Used for:
- Attendance optimization
- Minimum classes required

### 2. Mathematical Optimization

Needed classes:
```
x ≥ (R*T - A) / (1 - R)
```

Allowable absences:
```
x ≤ A/R - T
```

### 3. Sequential Mapping Algorithm
Maps:
```
start date + attendance → calendar visualization
```

---

## 🔐 Security

- Password hashing using SHA-256
- No plaintext password storage
- Secure login validation

---

## 🧩 Design Patterns

### Singleton Pattern
```
AttendanceService.getInstance()
```

### Observer Pattern
```
AttendanceChangeListener
```

### MVC-like Architecture

| Layer | Role |
|------|------|
| UI | Display |
| Service | Logic |
| Model | Data |

---

## 📁 Data Storage

Uses Java Serialization:

- File: `attendance_data.ser`
- Saves entire app state
- Fast read/write
- No external DB required

---

## 📦 Project Structure (Simplified)

- UI Layer → Swing Panels & Frames
- Service Layer → AttendanceService
- Data Layer → Models + DataStore

---

## ⚡ Performance

- Uses ArrayList & HashMap
- Minimal disk I/O
- Listener-based UI updates

---

## 🧼 Data Normalization

Handles:
- Missing fields
- Older file versions
- Prevents crashes

---

## 🔮 Future Improvements

- Database integration (MySQL / SQLite)
- REST API backend
- Attendance prediction (Backtracking)
- PDF export
- Mobile/Web version

---

## 💬 Final Note

This project demonstrates:

- Java Swing mastery
- Real-world problem solving
- Data structures & algorithms
- Clean UI architecture
- Debugging complex UI issues

---

Made with logic, patience, and way too many UI fixes 😄
