import java.util.ArrayList;

public class AttendanceManager {

    private final ArrayList<Subject> subjects = new ArrayList<>();

    public void addSubject(Subject subject) {
        if (subject != null) subjects.add(subject);
    }

    public ArrayList<Subject> getSubjects() { return subjects; }

    public double getOverallAttendance() {
        int total = 0, attended = 0;
        for (Subject s : subjects) {
            total    += s.totalClasses;
            attended += s.attendedClasses;
        }
        return total == 0 ? 0.0 : (attended * 100.0) / total;
    }
}
