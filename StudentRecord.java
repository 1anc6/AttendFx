import java.io.Serializable;

public class StudentRecord implements Serializable {

    private static final long serialVersionUID = 1L;

    public String name;
    public String rollNo;
    public String universityRollNo;
    public String classRollNo;
    public String section;
    public String course;
    public String email;
    public String phone;
    public String address;
    public String dateOfBirth;
    public String password;
    public String subject;
    public int totalClasses;
    public int attendedClasses;

    public StudentRecord(String name, String rollNo, String subject) {
        this.name = name;
        this.rollNo = rollNo;
        this.universityRollNo = rollNo;
        this.classRollNo = rollNo;
        this.section = "";
        this.course = "";
        this.email = "";
        this.phone = "";
        this.address = "";
        this.dateOfBirth = "";
        this.password = "";
        this.subject = subject;
        this.totalClasses = 0;
        this.attendedClasses = 0;
    }

    public StudentRecord(String name, String universityRollNo, String classRollNo, String section, String course) {
        this(name, universityRollNo, classRollNo, section, course, "");
    }

    public StudentRecord(String name, String universityRollNo, String classRollNo,
                         String section, String course, String password) {
        this.name = name;
        this.rollNo = universityRollNo;
        this.universityRollNo = universityRollNo;
        this.classRollNo = classRollNo;
        this.section = section;
        this.course = course;
        this.email = "";
        this.phone = "";
        this.address = "";
        this.dateOfBirth = "";
        this.password = password;
        this.subject = course;
        this.totalClasses = 0;
        this.attendedClasses = 0;
    }

    public double getAttendancePercentage() {
        if (totalClasses == 0) return 0.0;
        return (attendedClasses * 100.0) / totalClasses;
    }

    @Override
    public String toString() {
        return "StudentRecord{"
            + "name='" + name + '\''
            + ", universityRollNo='" + universityRollNo + '\''
            + ", classRollNo='" + classRollNo + '\''
            + ", section='" + section + '\''
            + ", course='" + course + '\''
            + '}';
    }
}
