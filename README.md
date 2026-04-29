# Student Attendance Dashboard

This is a Java Swing desktop application for managing student attendance. It includes student login, teacher login, signup, profile management, subject-wise attendance tracking, calendar-based daily attendance, dashboard summaries, and file-based persistence.

## How To Run

Compile all Java files from the project folder:

```bash
javac *.java
```

Run the application:

```bash
java Main
```

The app stores data in:

```text
attendance_data.ser
```

That file is created in the same folder as the project.

## Main Features

- Student and teacher login
- Student signup and teacher signup
- Student dashboard with attendance summary
- Student profile page with editable profile data
- Subject attendance table
- Add and delete subjects
- Calendar view for marking daily attendance
- Teacher dashboard for viewing and managing student records
- CSV export for teacher attendance data
- Automatic data saving after changes

## Project Structure

| File | Purpose |
|---|---|
| `Main.java` | Application entry point |
| `ModernLoginUI.java` | Login screen |
| `SignupUI.java` | Signup screen for students and teachers |
| `StudentDashboard.java` | Main student window |
| `TeacherDashboard.java` | Main teacher window |
| `MainPanel.java` | Switches student dashboard pages using `CardLayout` |
| `SidebarPanel.java` | Left navigation menu |
| `DashboardPanel.java` | Student dashboard summary and graph |
| `AttendanceInputPanel.java` | Session setup, subject table, add subject form |
| `RightPanel.java` | Calendar and attendance summary cards |
| `ProfilePanel.java` | Student profile page |
| `AttendanceService.java` | Main service layer and business logic |
| `DataStore.java` | Loads and saves application data |
| `AppData.java` | Serializable container for all saved data |
| `StudentRecord.java` | Student model |
| `TeacherRecord.java` | Teacher model |
| `Subject.java` | Subject attendance model |
| `AttendanceRecord.java` | Teacher-recorded attendance history model |
| `SessionInfo.java` | Academic session date range model |
| `AttendanceChangeListener.java` | Listener interface for UI updates |
| `RoundedPanel.java` | Reusable rounded panel component |
| `ShadowPanel.java` | Reusable shadow wrapper component |
| `HeaderPanel.java` | Header UI component |
| `PerformancePanel.java` | Circular performance display |
| `AttendanceManager.java` | Legacy helper class |

## Application Flow

1. `Main.java` starts the app on the Swing Event Dispatch Thread using `SwingUtilities.invokeLater`.
2. `ModernLoginUI.java` opens the login screen.
3. The user logs in as a student or teacher.
4. Login validation is handled by `AttendanceService`.
5. If login succeeds, either `StudentDashboard` or `TeacherDashboard` opens.
6. `AttendanceService` loads saved data through `DataStore`.
7. UI panels register themselves as listeners.
8. When data changes, `AttendanceService` saves the data and notifies listeners.
9. Listener panels refresh their table, graph, profile, calendar, or cards.

## Java Concepts Used

### Core Java

- Classes and objects
- Constructors
- Instance fields
- Static fields
- Static methods
- Access modifiers: `public`, `private`
- Method overloading
- Method overriding
- Interfaces
- Inner classes
- Anonymous inner classes
- Lambda expressions
- Collections: `List`, `ArrayList`, `Map`, `HashMap`
- Generics
- Streams
- String handling
- Date handling with `LocalDate`, `YearMonth`, `DayOfWeek`
- Exception handling with `try`, `catch`
- File handling
- Serialization
- Logging with `java.util.logging.Logger`
- Password hashing with `MessageDigest`

### Swing GUI Concepts

- `JFrame`
- `JPanel`
- `JLabel`
- `JButton`
- `JTextField`
- `JPasswordField`
- `JTable`
- `JScrollPane`
- `JOptionPane`
- `JComboBox`
- `CardLayout`
- `BorderLayout`
- `GridLayout`
- `GridBagLayout`
- `BoxLayout`
- `FlowLayout`
- Custom painting with `paintComponent`
- `Graphics`
- `Graphics2D`
- `GradientPaint`
- Mouse listeners
- Focus listeners
- Action listeners
- Table models with `DefaultTableModel`
- Table renderers
- Table editors
- Swing Event Dispatch Thread

### Design Concepts

- Layered architecture
- Model-service-UI separation
- Singleton pattern
- Observer/listener pattern
- File-based persistence
- Input validation
- UI refresh after data mutation
- Reusable UI components

## Architecture

The project is organized into three practical layers.

### UI Layer

The UI layer contains Swing screens and panels:

- `ModernLoginUI`
- `SignupUI`
- `StudentDashboard`
- `TeacherDashboard`
- `DashboardPanel`
- `AttendanceInputPanel`
- `RightPanel`
- `ProfilePanel`
- `SidebarPanel`
- `MainPanel`

These classes display data and collect user input. They do not directly save files. They call `AttendanceService` for login, profile updates, subject updates, attendance updates, and calculations.

### Service Layer

`AttendanceService.java` is the main business logic class.

It handles:

- Login validation
- Student registration
- Teacher registration
- Current logged-in student tracking
- Profile loading and saving
- Subject creation and deletion
- Attendance calculation
- Daily calendar attendance
- Teacher dashboard data
- CSV export
- Data normalization
- Listener notification
- Calling `DataStore.save(data)` after changes

`AttendanceService` is a singleton. The app uses:

```java
AttendanceService.getInstance()
```

This keeps one shared service object across all UI panels.

### Data Layer

The data layer is handled by:

- `DataStore.java`
- `AppData.java`
- model classes such as `StudentRecord`, `Subject`, `TeacherRecord`, `AttendanceRecord`, `SessionInfo`

`DataStore` reads and writes the full `AppData` object to `attendance_data.ser`.

## How Data Is Stored

The app uses Java built-in object serialization.

### Saved File

```text
attendance_data.ser
```

### Saving

`DataStore.save(AppData data)` uses:

```java
ObjectOutputStream
FileOutputStream
```

It writes the whole `AppData` object into the `.ser` file.

### Loading

`DataStore.load()` uses:

```java
ObjectInputStream
FileInputStream
```

It reads the `.ser` file and converts it back into an `AppData` object.

If the file does not exist, the app creates a new empty `AppData`.

If the file is corrupt or outdated, the app starts with clean data so the program does not crash.

## What AppData Stores

`AppData.java` is the main saved container.

It stores:

| Field | Meaning |
|---|---|
| `subjects` | List of subject attendance records |
| `students` | List of student profiles |
| `teachers` | List of teacher accounts |
| `currentStudentUniversityRollNo` | Active logged-in student identifier |
| `attendanceRecords` | Teacher-recorded attendance actions |
| `classesConductedTillNow` | Optional teacher override for total classes |
| `session` | Current academic session dates |
| `dailyAttendance` | Calendar day attendance map |

## Student Data Storage

Student data is stored in `StudentRecord`.

Important fields:

| Field | Meaning |
|---|---|
| `name` | Student name |
| `rollNo` | Legacy roll number field |
| `universityRollNo` | University roll number and main login identifier |
| `classRollNo` | Class roll number |
| `section` | Section |
| `course` | Course |
| `email` | Email |
| `phone` | Phone number |
| `address` | Address |
| `dateOfBirth` | Date of birth |
| `password` | Hashed password |
| `subject` | Legacy/default subject field |
| `totalClasses` | Total classes for older teacher flow |
| `attendedClasses` | Attended classes for older teacher flow |

When a student signs up, `AttendanceService.registerStudent` creates a `StudentRecord` and adds it to:

```java
data.students
```

When a student logs in, the service stores:

```java
data.currentStudentUniversityRollNo
```

The profile page uses that value to find the correct student record.

## Teacher Data Storage

Teacher accounts are stored in `TeacherRecord`.

Important fields:

| Field | Meaning |
|---|---|
| `username` | Teacher login name |
| `password` | Hashed password |

Teacher records are stored in:

```java
data.teachers
```

## Subject Data Storage

Each subject is stored as a `Subject`.

Important fields:

| Field | Meaning |
|---|---|
| `name` | Subject name |
| `totalClasses` | Total classes for that subject |
| `attendedClasses` | Classes attended |
| `studentId` | Owner student roll number |

Subjects are stored in:

```java
data.subjects
```

The `studentId` connects each subject to one student.

## Daily Calendar Attendance Storage

Calendar attendance is stored in:

```java
data.dailyAttendance
```

It is a `Map<String, Boolean>`.

The key format is:

```text
studentId|YYYY-MM-DD
```

Example:

```text
1|2026-01-05
```

The value means:

| Value | Meaning |
|---|---|
| `true` | Attended |
| `false` | Absent |
| missing key | Not marked |

Clicking a calendar day cycles through:

```text
Not marked -> Attended -> Absent -> Not marked
```

## Attendance Calculation

The required attendance percentage is:

```text
75%
```

This is stored in `AttendanceService` as:

```java
REQUIRED_PCT = 75.0
REQUIRED_FRACTION = 0.75
```

## Overall Attendance Formula

Overall attendance is calculated across all subjects for the logged-in student.

Formula:

```text
overall percentage = total attended classes / total classes * 100
```

Example:

```text
Subject 1: total 10, attended 9
Subject 2: total 11, attended 9

Total classes = 21
Total attended = 18

Attendance = 18 / 21 * 100
Attendance = 85.71%
```

The method used is:

```java
getOverallAttendance()
```

## Classes Needed Calculation

This calculates how many future classes must be attended continuously to reach 75%.

Let:

```text
T = current total classes
A = current attended classes
x = needed future attended classes
R = required fraction = 0.75
```

To reach the required percentage:

```text
(A + x) / (T + x) >= R
```

Solving:

```text
A + x >= R(T + x)
A + x >= RT + Rx
x - Rx >= RT - A
x(1 - R) >= RT - A
x >= (RT - A) / (1 - R)
```

The app uses:

```text
needed = ceil((0.75 * total - attended) / (1 - 0.75))
```

If the result is less than or equal to zero, needed classes is `0`.

The method used is:

```java
calculateNeeded(int total, int attended)
```

## Allowable Absences Calculation

This calculates how many future classes can be missed while still staying at or above 75%.

Let:

```text
T = current total classes
A = current attended classes
x = future absences allowed
R = required fraction = 0.75
```

If the student misses `x` future classes:

```text
A / (T + x) >= R
```

Solving:

```text
A >= R(T + x)
A / R >= T + x
x <= A / R - T
```

The app uses:

```text
allowable absences = floor(attended / 0.75 - total)
```

If the result is negative, allowable absences is `0`.

The method used is:

```java
calculateAllowableAbsences(int total, int attended)
```

## Total Needed And Total Allowable

The app calculates per-subject needed classes, then adds them:

```java
getTotalNeeded()
```

The app calculates per-subject allowable absences, then adds them:

```java
getTotalAllowable()
```

## Attendance Status

The app uses these status levels:

| Percentage | Status |
|---|---|
| `>= 75%` | `SAFE` |
| `>= 60%` and `< 75%` | `WARNING` |
| `< 60%` | `CRITICAL` |

The method used is:

```java
getStatusLabel(double percent)
```

For subjects, the app also checks whether reaching 75% is possible with the remaining working days.

The method used is:

```java
buildStatus(double percent, int needed)
```

## Working Days Calculation

The app counts working days between session start and end dates.

Sundays are treated as non-working days.

Formula:

```text
working days = total days - Sundays
```

The method used is:

```java
getWorkingDays(LocalDate start, LocalDate end)
```

## Password Handling

Passwords are not stored as plain text.

The app hashes passwords using:

```java
MessageDigest
SHA-256
```

During login:

1. The entered password is hashed.
2. The hash is compared with the saved hash.
3. Login succeeds only if the username and password hash match.

## Listener System

The app uses `AttendanceChangeListener` so panels update automatically.

Examples:

- When a subject is added, the table and dashboard refresh.
- When a calendar day is clicked, the calendar and summary cards refresh.
- When profile data changes, the profile and dashboard name refresh.
- When session dates change, the calendar refreshes.

This avoids direct coupling between UI panels.

## Important UI Pages

### Login Page

Handled by:

```text
ModernLoginUI.java
```

It validates student and teacher accounts through `AttendanceService`.

### Student Dashboard

Handled by:

```text
StudentDashboard.java
MainPanel.java
DashboardPanel.java
AttendanceInputPanel.java
RightPanel.java
ProfilePanel.java
```

The dashboard uses `CardLayout` to switch between:

- Dashboard
- Attendance
- Profile

### Teacher Dashboard

Handled by:

```text
TeacherDashboard.java
```

It can view students, attendance records, filters, totals, and export CSV data.

## Profile Loading

The student profile loads through:

```java
AttendanceService.getCurrentStudentProfile()
```

That method uses:

```java
data.currentStudentUniversityRollNo
```

Then it finds the matching student from:

```java
data.students
```

The profile fields are populated in `ProfilePanel.refreshProfile()`.

## Data Normalization

Older saved files may not contain every new field.

`AttendanceService` normalizes loaded data by filling missing values such as:

- missing student lists
- missing teacher lists
- missing attendance records
- missing daily attendance map
- missing `universityRollNo`
- missing `classRollNo`
- missing `section`
- missing `course`
- missing password hashes
- missing subject owner IDs

This helps older `attendance_data.ser` files continue working after code changes.

## CSV Export

Teacher dashboard export writes a CSV file with:

- University Roll No
- Class Roll No
- Name
- Course
- Section
- Total Classes
- Classes Attended
- Attendance %
- Status

The export is handled by:

```java
AttendanceService.exportAttendanceCsv(File file)
```

## Compile Notes

All Java files are in the default package, so compile from the project directory using:

```bash
javac *.java
```

Run with:

```bash
java Main
```

## Data Reset

To reset all saved app data, close the app and delete:

```text
attendance_data.ser
```

The next run will start with a new empty `AppData` object.
