import java.io.Serializable;

public class Subject implements Serializable {

    private static final long serialVersionUID = 1L;

    public String name;
    public String studentId;
    public int    totalClasses;
    public int    attendedClasses;

    public Subject(String name, int totalClasses, int attendedClasses) {
        this(name, totalClasses, attendedClasses, null);
    }

    public Subject(String name, int totalClasses, int attendedClasses, String studentId) {
        this.name            = name;
        this.studentId       = studentId;
        this.totalClasses    = totalClasses;
        this.attendedClasses = attendedClasses;
    }

    public String getName()          { return name; }
    public int    getTotalClasses()  { return totalClasses; }
    public int    getAttendedClasses(){ return attendedClasses; }

    public double getPercentage() {
        if (totalClasses == 0) return 0.0;
        return (attendedClasses * 100.0) / totalClasses;
    }

    @Override
    public String toString() {
        return String.format("Subject{name='%s', total=%d, attended=%d, pct=%.1f%%}",
            name, totalClasses, attendedClasses, getPercentage());
    }
}
