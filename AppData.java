import java.io.Serializable;
import java.util.*;

public class AppData implements Serializable {

    private static final long serialVersionUID = 1L;

    public List<Subject> subjects = new ArrayList<>();

    public List<StudentRecord> students = new ArrayList<>();

    public List<TeacherRecord> teachers = new ArrayList<>();

    public String currentStudentUniversityRollNo = null;

    public List<AttendanceRecord> attendanceRecords = new ArrayList<>();

    public Integer classesConductedTillNow = null;

    public SessionInfo session = null;

    public Map<String, Boolean> dailyAttendance = new HashMap<>();
}
