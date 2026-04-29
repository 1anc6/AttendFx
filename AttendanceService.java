import java.time.*;
import java.time.temporal.ChronoUnit;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.*;
import java.util.logging.Logger;

public class AttendanceService {

    public  static final double REQUIRED_PCT      = 75.0;
    public  static final double WARNING_PCT       = 60.0;
    private static final double REQUIRED_FRACTION = REQUIRED_PCT / 100.0;
    public  static final int    CLASSES_PER_WEEK  = 5;

    private static final Logger LOGGER = Logger.getLogger(AttendanceService.class.getName());

    private static AttendanceService instance;

    public static AttendanceService getInstance() {
        if (instance == null) {
            instance = new AttendanceService();
        }
        return instance;
    }

    private final AppData data;
    private final List<AttendanceChangeListener> listeners = new ArrayList<>();
    private String calendarSubjectFilter = null;

    private AttendanceService() {
        data = DataStore.load();
        normalizeLoadedData();
        LOGGER.info("AttendanceService initialized with " +
            data.subjects.size() + " subject(s).");
    }

    private void normalizeLoadedData() {
        if (data.subjects == null) data.subjects = new ArrayList<>();
        if (data.students == null) data.students = new ArrayList<>();
        if (data.teachers == null) data.teachers = new ArrayList<>();
        if (data.attendanceRecords == null) data.attendanceRecords = new ArrayList<>();
        if (data.dailyAttendance == null) data.dailyAttendance = new HashMap<>();
        for (StudentRecord student : data.students) normalizeStudentRecord(student);
        normalizePasswords();
        normalizeSubjects();
    }

    public void addListener(AttendanceChangeListener l) {
        if (l != null && !listeners.contains(l)) listeners.add(l);
    }

    public void notifyDataLoaded() {
        listeners.forEach(AttendanceChangeListener::onDataLoaded);
        if (data.session != null)
            listeners.forEach(l -> l.onSessionChanged(data.session));
    }

    public boolean isSessionSet()   { return data.session != null; }
    public SessionInfo getSession() { return data.session; }

    public boolean setSession(String startStr, String endStr) {
        try {
            LocalDate start = LocalDate.parse(startStr.trim());
            LocalDate end   = LocalDate.parse(endStr.trim());
            data.session    = new SessionInfo(start, end);
            DataStore.save(data);
            listeners.forEach(l -> l.onSessionChanged(data.session));
            return true;
        } catch (IllegalArgumentException e) {
            LOGGER.warning("Invalid session dates: " + e.getMessage());
            return false;
        } catch (Exception e) {
            LOGGER.warning("Session parse error: " + e.getMessage());
            return false;
        }
    }

    public List<Subject> getSubjects() {
        String currentStudentId = getCurrentStudentId();
        if (currentStudentId == null) return Collections.emptyList();
        return Collections.unmodifiableList(getSubjectsOwnedBy(currentStudentId));
    }

    public List<Subject> getSubjectsForStudent(String universityRollNo) {
        if (universityRollNo == null || universityRollNo.trim().isEmpty()) {
            return Collections.emptyList();
        }
        return Collections.unmodifiableList(getSubjectsOwnedBy(universityRollNo.trim()));
    }

    public int[] getSubjectTotalsForStudent(String universityRollNo) {
        int totalClasses = 0;
        int attendedClasses = 0;

        for (Subject subject : getSubjectsForStudent(universityRollNo)) {
            totalClasses += subject.totalClasses;
            attendedClasses += subject.attendedClasses;
        }

        return new int[] { totalClasses, attendedClasses };
    }

    public String addSubject(String name, String totalStr, String attendedStr) {
        if (name == null || name.trim().isEmpty())
            return "Subject name cannot be empty.";

        int total, attended;
        try {
            total    = Integer.parseInt(totalStr.trim());
            attended = Integer.parseInt(attendedStr.trim());
        } catch (NumberFormatException e) {
            return "Total and Attended must be whole numbers.";
        }

        if (total <= 0)             return "Total classes must be greater than 0.";
        if (attended < 0)           return "Attended classes cannot be negative.";
        if (attended > total)       return "Attended cannot exceed total classes.";

        String currentStudentId = getCurrentStudentId();
        if (currentStudentId == null)
            return "Please login as a student before adding subjects.";

        Subject s = new Subject(name.trim(), total, attended, currentStudentId);
        data.subjects.add(s);
        DataStore.save(data);
        listeners.forEach(l -> l.onSubjectAdded(s));
        return null; 
    }

    public List<StudentRecord> getStudents() {
        return Collections.unmodifiableList(data.students);
    }

    public List<AttendanceRecord> getAttendanceRecords() {
        return Collections.unmodifiableList(data.attendanceRecords);
    }

    public boolean isTeacherLogin(String username, String password) {
        String enteredUsername = username == null ? "" : username.trim();
        String enteredPasswordHash = hashPassword(password);
        LOGGER.info("Teacher login attempt username=" + enteredUsername);

        if ("teacher".equalsIgnoreCase(enteredUsername) && hashPassword("1234").equals(enteredPasswordHash)) return true;
        for (TeacherRecord teacher : data.teachers) {
            String savedUsername = teacher.username == null ? "" : teacher.username.trim();
            String savedPassword = teacher.password == null ? "" : teacher.password.trim();
            LOGGER.info("Checking teacher record username=" + savedUsername);

            if (savedUsername.equalsIgnoreCase(enteredUsername) && savedPassword.equals(enteredPasswordHash)) {
                return true;
            }
        }
        return false;
    }

    public boolean isStudentLogin(String username, String password) {
        String enteredUsername = username == null ? "" : username.trim();
        String enteredPasswordHash = hashPassword(password);
        LOGGER.info("Student login attempt username=" + enteredUsername);

        if ("student".equalsIgnoreCase(enteredUsername) && hashPassword("1234").equals(enteredPasswordHash)) {
            data.currentStudentUniversityRollNo = "student";
            DataStore.save(data);
            return true;
        }
        for (StudentRecord student : data.students) {
            normalizeStudentRecord(student);
            String savedUniversityRoll = student.universityRollNo == null ? "" : student.universityRollNo.trim();
            String savedName = student.name == null ? "" : student.name.trim();
            String savedPassword = student.password == null ? "" : student.password.trim();
            LOGGER.info("Checking student record name=" + savedName
                + ", universityRollNo=" + savedUniversityRoll);

            boolean usernameMatches = savedUniversityRoll.equalsIgnoreCase(enteredUsername)
                || savedName.equalsIgnoreCase(enteredUsername);
            if (usernameMatches && savedPassword.equals(enteredPasswordHash)) {
                data.currentStudentUniversityRollNo = student.universityRollNo;
                DataStore.save(data);
                return true;
            }
        }
        return false;
    }

    public String registerTeacher(String username, String password) {
        if (username == null || username.trim().isEmpty()) return "Username cannot be empty.";
        if (password == null || password.trim().isEmpty()) return "Password cannot be empty.";

        String cleanUsername = username.trim();
        if ("student".equalsIgnoreCase(cleanUsername) || "teacher".equalsIgnoreCase(cleanUsername)) {
            return "This username is reserved.";
        }
        for (TeacherRecord teacher : data.teachers) {
            if (teacher.username != null && teacher.username.equalsIgnoreCase(cleanUsername)) {
                return "Username already exists.";
            }
        }
        for (StudentRecord student : data.students) {
            normalizeStudentRecord(student);
            if (student.universityRollNo.equalsIgnoreCase(cleanUsername)) {
                return "Username already exists.";
            }
        }

        data.teachers.add(new TeacherRecord(cleanUsername, hashPassword(password)));
        DataStore.save(data);
        return null;
    }

    public String registerStudent(String name, String universityRollNo, String classRollNo,
                                  String section, String course, String password) {
        if (name == null || name.trim().isEmpty()) return "Student name cannot be empty.";
        if (universityRollNo == null || universityRollNo.trim().isEmpty()) return "University roll no cannot be empty.";
        if (classRollNo == null || classRollNo.trim().isEmpty()) return "Class roll no cannot be empty.";
        if (section == null || section.trim().isEmpty()) return "Section cannot be empty.";
        if (course == null || course.trim().isEmpty()) return "Course cannot be empty.";
        if (password == null || password.trim().isEmpty()) return "Password cannot be empty.";

        String universityRoll = universityRollNo.trim();
        StudentRecord existing = findStudentByUniversityRoll(universityRoll);
        if (existing != null) return "A student with this university roll no already exists.";
        for (StudentRecord student : data.students) {
            normalizeStudentRecord(student);
            if (student.name != null && student.name.trim().equalsIgnoreCase(name.trim())) {
                return "A student with this username already exists.";
            }
            if (student.classRollNo.equalsIgnoreCase(classRollNo.trim())) {
                return "A student with this class roll no already exists.";
            }
        }
        for (TeacherRecord teacher : data.teachers) {
            if (teacher.username != null && teacher.username.equalsIgnoreCase(universityRoll)) {
                return "University roll no is already used as a teacher username.";
            }
            if (teacher.username != null && teacher.username.equalsIgnoreCase(name.trim())) {
                return "Student name is already used as a teacher username.";
            }
        }

        StudentRecord student = new StudentRecord(
            name.trim(), universityRoll, classRollNo.trim(), section.trim(), course.trim(), hashPassword(password)
        );
        if (data.classesConductedTillNow != null) student.totalClasses = data.classesConductedTillNow;

        data.students.add(student);

        DataStore.save(data);
        notifyAllDataChanged();
        return null;
    }

    public StudentRecord getCurrentStudentProfile() {
        if (data.currentStudentUniversityRollNo != null) {
            StudentRecord selected = findStudentByUniversityRoll(data.currentStudentUniversityRollNo);
            if (selected != null) return selected;
        }
        return null;
    }

    public String updateCurrentStudentProfile(String name, String universityRollNo, String classRollNo,
                                              String section, String course, String email,
                                              String phone, String address, String dateOfBirth) {
        StudentRecord student = getCurrentStudentProfile();
        if (student == null) return "No logged-in student profile found.";
        if (name == null || name.trim().isEmpty()) return "Name cannot be empty.";
        if (universityRollNo == null || universityRollNo.trim().isEmpty()) return "University roll no cannot be empty.";
        if (classRollNo == null || classRollNo.trim().isEmpty()) return "Class roll no cannot be empty.";
        if (section == null || section.trim().isEmpty()) return "Section cannot be empty.";
        if (course == null || course.trim().isEmpty()) return "Course cannot be empty.";
        if (email != null && !email.trim().isEmpty()
            && !email.trim().matches("^[A-Za-z0-9+_.-]+@[A-Za-z0-9.-]+$")) return "Invalid email format.";
        if (phone != null && !phone.trim().isEmpty()
            && !phone.trim().matches("\\d+")) return "Phone number must contain digits only.";

        String newUniversityRoll = universityRollNo.trim();
        for (StudentRecord other : data.students) {
            if (other != student && other.universityRollNo != null
                && other.universityRollNo.equalsIgnoreCase(newUniversityRoll)) {
                return "University roll no already exists.";
            }
        }

        String oldUniversityRoll = student.universityRollNo;
        student.name = name.trim();
        student.rollNo = newUniversityRoll;
        student.universityRollNo = newUniversityRoll;
        student.classRollNo = classRollNo.trim();
        student.section = section.trim();
        student.course = course.trim();
        student.email = clean(email);
        student.phone = clean(phone);
        student.address = clean(address);
        student.dateOfBirth = clean(dateOfBirth);
        data.currentStudentUniversityRollNo = newUniversityRoll;

        for (Subject subject : data.subjects) {
            if (subject.studentId != null && subject.studentId.equalsIgnoreCase(oldUniversityRoll)) {
                subject.studentId = newUniversityRoll;
            }
        }
        DataStore.save(data);
        notifyAllDataChanged();
        return null;
    }

    public String addStudent(String name, String rollNo, String subject) {
        if (name == null || name.trim().isEmpty()) return "Student name cannot be empty.";
        if (rollNo == null || rollNo.trim().isEmpty()) return "Roll number cannot be empty.";
        if (subject == null || subject.trim().isEmpty()) return "Subject cannot be empty.";

        String cleanRoll = rollNo.trim();
        for (StudentRecord s : data.students) {
            if (s.rollNo.equalsIgnoreCase(cleanRoll)) return "A student with this roll number already exists.";
        }

        String cleanSubject = subject.trim();
        StudentRecord student = new StudentRecord(name.trim(), cleanRoll, cleanRoll, "", cleanSubject);
        if (data.classesConductedTillNow != null) student.totalClasses = data.classesConductedTillNow;
        data.students.add(student);
        ensureSubjectExists(cleanSubject, cleanRoll);
        DataStore.save(data);
        listeners.forEach(AttendanceChangeListener::onTeacherDataChanged);
        listeners.forEach(AttendanceChangeListener::onDataLoaded);
        return null;
    }

    public String addStudentProfile(String name, String universityRollNo, String classRollNo,
                                    String section, String course) {
        if (name == null || name.trim().isEmpty()) return "Student name cannot be empty.";
        if (universityRollNo == null || universityRollNo.trim().isEmpty()) return "University roll no cannot be empty.";
        if (classRollNo == null || classRollNo.trim().isEmpty()) return "Class roll no cannot be empty.";
        if (section == null || section.trim().isEmpty()) return "Section cannot be empty.";
        if (course == null || course.trim().isEmpty()) return "Course cannot be empty.";

        String cleanUniversityRoll = universityRollNo.trim();
        String cleanClassRoll = classRollNo.trim();
        if (findStudentByUniversityRoll(cleanUniversityRoll) != null) return "A student with this university roll no already exists.";
        for (StudentRecord student : data.students) {
            normalizeStudentRecord(student);
            if (student.classRollNo.equalsIgnoreCase(cleanClassRoll)) return "A student with this class roll no already exists.";
        }

        StudentRecord student = new StudentRecord(
            name.trim(), cleanUniversityRoll, cleanClassRoll, section.trim(), course.trim()
        );
        if (data.classesConductedTillNow != null) student.totalClasses = data.classesConductedTillNow;
        data.students.add(student);
        ensureSubjectExists(course.trim(), cleanUniversityRoll);
        DataStore.save(data);
        notifyAllDataChanged();
        return null;
    }

    public String updateStudentProfileByUniversityRoll(String originalUniversityRollNo, String name,
                                                       String universityRollNo, String classRollNo,
                                                       String section, String course) {
        if (originalUniversityRollNo == null || originalUniversityRollNo.trim().isEmpty()) return "No student selected.";
        StudentRecord student = findStudentByUniversityRoll(originalUniversityRollNo.trim());
        if (student == null) return "Selected student was not found.";
        if (name == null || name.trim().isEmpty()) return "Student name cannot be empty.";
        if (universityRollNo == null || universityRollNo.trim().isEmpty()) return "University roll no cannot be empty.";
        if (classRollNo == null || classRollNo.trim().isEmpty()) return "Class roll no cannot be empty.";
        if (section == null || section.trim().isEmpty()) return "Section cannot be empty.";
        if (course == null || course.trim().isEmpty()) return "Course cannot be empty.";

        String cleanUniversityRoll = universityRollNo.trim();
        String cleanClassRoll = classRollNo.trim();
        for (StudentRecord other : data.students) {
            normalizeStudentRecord(other);
            if (other != student && other.universityRollNo.equalsIgnoreCase(cleanUniversityRoll)) {
                return "A student with this university roll no already exists.";
            }
            if (other != student && other.classRollNo.equalsIgnoreCase(cleanClassRoll)) {
                return "A student with this class roll no already exists.";
            }
        }

        String oldUniversityRoll = student.universityRollNo;
        student.name = name.trim();
        student.rollNo = cleanUniversityRoll;
        student.universityRollNo = cleanUniversityRoll;
        student.classRollNo = cleanClassRoll;
        student.section = section.trim();
        student.course = course.trim();
        student.subject = course.trim();
        for (Subject subject : data.subjects) {
            if (subject.studentId != null && subject.studentId.equalsIgnoreCase(oldUniversityRoll)) {
                subject.studentId = cleanUniversityRoll;
            }
        }
        for (AttendanceRecord record : data.attendanceRecords) {
            if (record.rollNo != null && record.rollNo.equalsIgnoreCase(oldUniversityRoll)) {
                record.rollNo = cleanUniversityRoll;
            }
        }
        if (data.currentStudentUniversityRollNo != null
            && data.currentStudentUniversityRollNo.equalsIgnoreCase(oldUniversityRoll)) {
            data.currentStudentUniversityRollNo = cleanUniversityRoll;
        }
        ensureSubjectExists(course.trim(), cleanUniversityRoll);
        DataStore.save(data);
        notifyAllDataChanged();
        return null;
    }

    public String recordStudentAttendance(String rollNo, boolean present) {
        return recordStudentAttendance(rollNo, LocalDate.now(), present);
    }

    public String recordStudentAttendance(String rollNo, LocalDate date, boolean present) {
        if (rollNo == null || rollNo.trim().isEmpty()) return "Please select a student.";
        if (date == null) return "Attendance date is required.";

        StudentRecord student = findStudentByRoll(rollNo.trim());
        if (student == null) return "Selected student was not found.";
        if (present && data.classesConductedTillNow != null
            && student.attendedClasses >= data.classesConductedTillNow) {
            return "Attended classes cannot exceed total classes conducted.";
        }

        if (data.classesConductedTillNow == null) student.totalClasses++;
        if (present) student.attendedClasses++;

        Subject subject = ensureSubjectExists(student.subject, student.universityRollNo);
        if (data.classesConductedTillNow == null) subject.totalClasses++;
        if (present) subject.attendedClasses++;

        data.attendanceRecords.add(new AttendanceRecord(
            student.rollNo, student.subject, date, present
        ));

        DataStore.save(data);
        listeners.forEach(AttendanceChangeListener::onTeacherDataChanged);
        listeners.forEach(AttendanceChangeListener::onDataLoaded);
        return null;
    }

    public String deleteStudent(String rollNo) {
        if (rollNo == null || rollNo.trim().isEmpty()) return "No student selected.";

        StudentRecord student = findStudentByRoll(rollNo.trim());
        if (student == null) return "Deletion failed: student not found.";

        String studentId = student.universityRollNo;
        data.students.remove(student);
        data.subjects.removeIf(s -> belongsToStudent(s, studentId));
        data.attendanceRecords.removeIf(r -> r.rollNo.equalsIgnoreCase(student.rollNo)
            || r.rollNo.equalsIgnoreCase(studentId));

        boolean subjectStillAssigned = false;
        for (StudentRecord s : data.students) {
            if (s.subject.equalsIgnoreCase(student.subject)) {
                subjectStillAssigned = true;
                break;
            }
        }

        if (!subjectStillAssigned) {
            data.subjects.removeIf(s -> s.name.equalsIgnoreCase(student.subject));
            data.attendanceRecords.removeIf(r -> r.subject.equalsIgnoreCase(student.subject));
        }

        DataStore.save(data);
        notifyAllDataChanged();
        return null;
    }

    public String deleteSubject(String subjectName) {
        if (subjectName == null || subjectName.trim().isEmpty()) return "No subject selected.";

        String currentStudentId = getCurrentStudentId();
        if (currentStudentId == null) return "No active student session.";

        boolean removed = data.subjects.removeIf(s ->
            belongsToStudent(s, currentStudentId) && s.name.equalsIgnoreCase(subjectName.trim()));
        if (!removed) return "Deletion failed: subject not found.";

        data.attendanceRecords.removeIf(r ->
            r.rollNo.equalsIgnoreCase(currentStudentId) && r.subject.equalsIgnoreCase(subjectName.trim()));
        for (StudentRecord student : data.students) {
            if (student.subject.equalsIgnoreCase(subjectName.trim())) {
                student.totalClasses = 0;
                student.attendedClasses = 0;
            }
        }

        DataStore.save(data);
        notifyAllDataChanged();
        return null;
    }

    public String setClassesConductedTillNow(String value) {
        int classes;
        try {
            classes = Integer.parseInt(value.trim());
        } catch (Exception e) {
            return "Total classes must be a whole number.";
        }

        if (classes < 0) return "Total classes cannot be negative.";

        for (StudentRecord student : data.students) {
            if (classes < student.attendedClasses) {
                return "Total classes cannot be less than attended classes for " + student.name + ".";
            }
        }
        for (Subject subject : getSubjects()) {
            if (classes < subject.attendedClasses) {
                return "Total classes cannot be less than attended classes for " + subject.name + ".";
            }
        }

        data.classesConductedTillNow = classes;
        for (StudentRecord student : data.students) student.totalClasses = classes;
        for (Subject subject : data.subjects) subject.totalClasses = classes;

        DataStore.save(data);
        notifyAllDataChanged();
        return null;
    }

    public int getTotalStudents() {
        return data.students.size();
    }

    public int getTotalWorkingDaysInSession() {
        if (data.session == null) return 0;
        return getWorkingDays(data.session.getStartDate(), data.session.getEndDate());
    }

    public int getClassesTillToday() {
        if (data.classesConductedTillNow != null) return data.classesConductedTillNow;
        if (data.session == null) return 0;
        LocalDate today = LocalDate.now();
        if (today.isBefore(data.session.getStartDate())) return 0;
        LocalDate end = today.isAfter(data.session.getEndDate()) ? data.session.getEndDate() : today;
        return getWorkingDays(data.session.getStartDate(), end);
    }

    public int getStoredClassesConductedTillNow() {
        return data.classesConductedTillNow == null ? -1 : data.classesConductedTillNow;
    }

    public double getAverageStudentAttendance() {
        int total = 0, attended = 0;
        for (StudentRecord s : data.students) {
            int[] totals = getSubjectTotalsForStudent(s.universityRollNo);
            total += totals[0];
            attended += totals[1];
        }
        return total == 0 ? 0.0 : (attended * 100.0) / total;
    }

    public int getSafeMissableClasses() {
        int total = getTotalClasses();
        int attended = getTotalAttended();
        if (total == 0) return 0;

        int misses = 0;
        while ((attended * 100.0) / (total + misses + 1) >= REQUIRED_PCT) {
            misses++;
        }
        return misses;
    }

    public String exportAttendanceCsv(File file) {
        if (file == null) return "Export file is required.";

        try (PrintWriter out = new PrintWriter(new OutputStreamWriter(
                new FileOutputStream(file), StandardCharsets.UTF_8))) {
            out.println("University Roll No,Class Roll No,Name,Course,Section,Total Classes,Classes Attended,Attendance %,Status");
            for (StudentRecord student : data.students) {
                int[] totals = getSubjectTotalsForStudent(student.universityRollNo);
                double pct = totals[0] == 0 ? 0.0 : (totals[1] * 100.0) / totals[0];
                out.printf(Locale.US, "%s,%s,%s,%s,%s,%d,%d,%.2f,%s%n",
                    csv(student.universityRollNo), csv(student.classRollNo), csv(student.name),
                    csv(student.course), csv(student.section), totals[0], totals[1], pct, getStatusLabel(pct));
            }
            return null;
        } catch (IOException e) {
            LOGGER.warning("CSV export failed: " + e.getMessage());
            return "Export failed: " + e.getMessage();
        }
    }

    private StudentRecord findStudentByRoll(String rollNo) {
        for (StudentRecord s : data.students) {
            if (s.rollNo.equalsIgnoreCase(rollNo)) return s;
        }
        return null;
    }

    private StudentRecord findStudentByUniversityRoll(String universityRollNo) {
        for (StudentRecord s : data.students) {
            normalizeStudentRecord(s);
            if (s.universityRollNo.equalsIgnoreCase(universityRollNo)) return s;
        }
        return null;
    }

    private void normalizeStudentRecord(StudentRecord student) {
        if (student == null) return;
        if (student.universityRollNo == null || student.universityRollNo.trim().isEmpty())
            student.universityRollNo = student.rollNo;
        if (student.classRollNo == null || student.classRollNo.trim().isEmpty())
            student.classRollNo = student.rollNo;
        if (student.section == null) student.section = "";
        if (student.email == null) student.email = "";
        if (student.phone == null) student.phone = "";
        if (student.address == null) student.address = "";
        if (student.dateOfBirth == null) student.dateOfBirth = "";
        if (student.password == null) student.password = "";
        if (student.course == null || student.course.trim().isEmpty())
            student.course = student.subject == null ? "" : student.subject;
        if (student.subject == null || student.subject.trim().isEmpty())
            student.subject = student.course == null || student.course.trim().isEmpty() ? "General" : student.course;
        if (student.rollNo == null || student.rollNo.trim().isEmpty())
            student.rollNo = student.universityRollNo;
    }

    private void normalizePasswords() {
        boolean changed = false;
        for (StudentRecord student : data.students) {
            if (student.password != null && !isSha256(student.password)) {
                student.password = hashPassword(student.password);
                changed = true;
            }
        }
        for (TeacherRecord teacher : data.teachers) {
            if (teacher.password != null && !isSha256(teacher.password)) {
                teacher.password = hashPassword(teacher.password);
                changed = true;
            }
        }
        if (changed) DataStore.save(data);
    }

    private boolean isSha256(String value) {
        return value != null && value.matches("[a-fA-F0-9]{64}");
    }

    private String hashPassword(String password) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest((password == null ? "" : password.trim()).getBytes(StandardCharsets.UTF_8));
            StringBuilder sb = new StringBuilder();
            for (byte b : hash) sb.append(String.format("%02x", b));
            return sb.toString();
        } catch (Exception e) {
            LOGGER.warning("Password hashing failed: " + e.getMessage());
            return "";
        }
    }

    private String csv(String value) {
        String clean = value == null ? "" : value.replace("\"", "\"\"");
        return "\"" + clean + "\"";
    }

    private String clean(String value) {
        return value == null ? "" : value.trim();
    }

    private Subject ensureSubjectExists(String subjectName, String studentId) {
        String cleanName = subjectName == null ? "General" : subjectName.trim();
        if (cleanName.isEmpty()) cleanName = "General";

        for (Subject s : data.subjects) {
            if (belongsToStudent(s, studentId) && s.name.equalsIgnoreCase(cleanName)) return s;
        }

        Subject created = new Subject(cleanName, 0, 0, studentId);
        if (data.classesConductedTillNow != null) created.totalClasses = data.classesConductedTillNow;
        data.subjects.add(created);
        return created;
    }

    private String getCurrentStudentId() {
        return data.currentStudentUniversityRollNo == null
            || data.currentStudentUniversityRollNo.trim().isEmpty()
                ? null
                : data.currentStudentUniversityRollNo.trim();
    }

    private List<Subject> getSubjectsOwnedBy(String studentId) {
        List<Subject> result = new ArrayList<>();
        for (Subject subject : data.subjects) {
            if (belongsToStudent(subject, studentId)) result.add(subject);
        }
        return result;
    }

    private boolean belongsToStudent(Subject subject, String studentId) {
        if (subject == null || studentId == null) return false;
        return subject.studentId != null && subject.studentId.equalsIgnoreCase(studentId.trim());
    }

    private void normalizeSubjects() {
        String fallbackOwner = getCurrentStudentId();
        if (fallbackOwner == null) fallbackOwner = "student";

        data.subjects.removeIf(s -> s == null || "BTECH".equalsIgnoreCase(s.name));
        for (Subject subject : data.subjects) {
            if (subject.studentId == null || subject.studentId.trim().isEmpty()) {
                subject.studentId = fallbackOwner;
            }
        }
        DataStore.save(data);
    }

    private void notifyAllDataChanged() {
        listeners.forEach(AttendanceChangeListener::onTeacherDataChanged);
        listeners.forEach(AttendanceChangeListener::onDataLoaded);
    }

    public void toggleDailyAttendance(LocalDate date) {
        if (date == null) return;
        String key     = dailyKey(date);
        Boolean current = data.dailyAttendance.get(key);

        Boolean next;
        if (current == null)  next = true;
        else if (current)     next = false;
        else                  next = null;

        if (next == null) data.dailyAttendance.remove(key);
        else              data.dailyAttendance.put(key, next);

        DataStore.save(data);
        final Boolean finalNext = next;
        listeners.forEach(l -> l.onDailyAttendanceChanged(date, finalNext));
    }

    public Boolean getDailyAttendance(LocalDate date) {
        if (date == null) return null;
        return data.dailyAttendance.get(dailyKey(date));
    }

    public Boolean getCalendarAttendanceStatus(LocalDate date) {
        java.util.List<Subject> subjects = getCalendarSubjects();
        int dayIndex = getClassDayIndex(date);
        if (dayIndex <= 0 || subjects.isEmpty()) return null;
        boolean hasClass = false;
        boolean anyAbsent = false;
        for (Subject subject : subjects) {
            if (dayIndex <= subject.totalClasses) {
                hasClass = true;
                if (dayIndex > subject.attendedClasses) anyAbsent = true;
            }
        }
        if (!hasClass) return null;
        return anyAbsent ? Boolean.FALSE : Boolean.TRUE;
    }

    public int getCalendarClassCount(LocalDate date) {
        java.util.List<Subject> subjects = getCalendarSubjects();
        int dayIndex = getClassDayIndex(date);
        if (dayIndex <= 0) return 0;
        int count = 0;
        for (Subject subject : subjects) {
            if (dayIndex <= subject.totalClasses) count++;
        }
        return count;
    }

    public java.util.Map<String, String> getCalendarSubjectStatuses(LocalDate date) {
        java.util.LinkedHashMap<String, String> result = new java.util.LinkedHashMap<>();
        java.util.List<Subject> subjects = getCalendarSubjects();
        int dayIndex = getClassDayIndex(date);
        if (dayIndex <= 0) return result;
        for (Subject subject : subjects) {
            if (dayIndex <= subject.totalClasses) {
                result.put(subject.name, dayIndex <= subject.attendedClasses ? "Present" : "Absent");
            }
        }
        return result;
    }

    public void setCalendarSubjectFilter(String subjectName) {
        String clean = subjectName == null || subjectName.trim().isEmpty() ? null : subjectName.trim();
        if (Objects.equals(calendarSubjectFilter, clean)) return;
        calendarSubjectFilter = clean;
        listeners.forEach(l -> l.onDailyAttendanceChanged(null, null));
    }

    public String getCalendarSubjectFilter() {
        return calendarSubjectFilter;
    }

    private java.util.List<Subject> getCalendarSubjects() {
        java.util.List<Subject> subjects = new ArrayList<>(getSubjects());
        if (calendarSubjectFilter == null) return subjects;
        subjects.removeIf(subject -> !subject.name.equalsIgnoreCase(calendarSubjectFilter));
        return subjects;
    }

    private int getClassDayIndex(LocalDate date) {
        if (date == null || data.session == null || !data.session.contains(date)) return 0;
        if (date.getDayOfWeek() == DayOfWeek.SUNDAY) return 0;
        int index = 0;
        LocalDate cursor = data.session.getStartDate();
        while (!cursor.isAfter(date)) {
            if (cursor.getDayOfWeek() != DayOfWeek.SUNDAY) index++;
            cursor = cursor.plusDays(1);
        }
        return index;
    }

    public java.util.List<AttendanceRecord> getCurrentStudentAttendanceRecords(LocalDate date) {
        String studentId = getCurrentStudentId();
        java.util.List<AttendanceRecord> result = new ArrayList<>();
        if (studentId == null || date == null) return result;
        for (AttendanceRecord record : data.attendanceRecords) {
            if (record != null
                && record.date != null
                && record.rollNo != null
                && record.date.equals(date)
                && record.rollNo.equalsIgnoreCase(studentId)) {
                result.add(record);
            }
        }
        return result;
    }

    private String dailyKey(LocalDate date) {
        String studentId = getCurrentStudentId();
        return (studentId == null ? "student" : studentId) + "|" + date.toString();
    }

    public double getOverallAttendance() {
        int total = 0, attended = 0;
        for (Subject s : getSubjects()) {
            total    += s.totalClasses;
            attended += s.attendedClasses;
        }
        return total == 0 ? 0.0 : (attended * 100.0) / total;
    }

    public int getTotalClasses()    { return getSubjects().stream().mapToInt(s -> s.totalClasses).sum(); }
    public int getTotalAttended()   { return getSubjects().stream().mapToInt(s -> s.attendedClasses).sum(); }
    public int getTotalAbsent()     { return getTotalClasses() - getTotalAttended(); }

    public int calculateNeeded(int total, int attended) {
        double needed = (REQUIRED_FRACTION * total - attended) / (1 - REQUIRED_FRACTION);
        return needed <= 0 ? 0 : (int) Math.ceil(needed);
    }

    public int calculateAllowableAbsences(int total, int attended) {
        double max = (attended / REQUIRED_FRACTION) - total;
        return (int) Math.max(0, Math.floor(max));
    }

    public int getTotalNeeded() {
        return getSubjects().stream()
            .mapToInt(s -> calculateNeeded(s.totalClasses, s.attendedClasses)).sum();
    }

    public int getTotalAllowable() {
        return getSubjects().stream()
            .mapToInt(s -> calculateAllowableAbsences(s.totalClasses, s.attendedClasses)).sum();
    }

    public int getWorkingDays(LocalDate start, LocalDate end) {
        if (start == null || end == null || end.isBefore(start)) return 0;
        try {
            long totalDays = ChronoUnit.DAYS.between(start, end) + 1;
            long fullWeeks = totalDays / 7;
            long remainder = totalDays % 7;
            long sundaysInRemainder = 0;
            for (int i = 0; i < remainder; i++) {
                if (start.plusDays(fullWeeks * 7 + i).getDayOfWeek() == DayOfWeek.SUNDAY)
                    sundaysInRemainder++;
            }
            return (int) (totalDays - fullWeeks - sundaysInRemainder);
        } catch (Exception e) {
            LOGGER.warning("getWorkingDays error: " + e.getMessage());
            return 0;
        }
    }

    public int getRemainingWorkingDays() {
        if (data.session == null) return 0;
        return getWorkingDays(data.session.getStartDate(), data.session.getEndDate());
    }

    public String buildStatus(double percent, int needed) {
        int remaining = getRemainingWorkingDays() * CLASSES_PER_WEEK / 7;
        String feasibility = (needed > remaining) ? "NOT POSSIBLE" : "POSSIBLE";
        return getStatusLabel(percent) + " / " + feasibility;
    }

    public String getStatusLabel(double percent) {
        if (percent >= REQUIRED_PCT) return "SAFE";
        if (percent >= WARNING_PCT)  return "WARNING";
        return "CRITICAL";
    }
}
