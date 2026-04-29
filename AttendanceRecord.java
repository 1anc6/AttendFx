import java.io.Serializable;
import java.time.LocalDate;

public class AttendanceRecord implements Serializable {

    private static final long serialVersionUID = 1L;

    public String rollNo;
    public String subject;
    public LocalDate date;
    public boolean present;

    public AttendanceRecord(String rollNo, String subject, LocalDate date, boolean present) {
        this.rollNo = rollNo;
        this.subject = subject;
        this.date = date;
        this.present = present;
    }
}
