import java.io.Serializable;

public class TeacherRecord implements Serializable {

    private static final long serialVersionUID = 1L;

    public String username;
    public String password;

    public TeacherRecord(String username, String password) {
        this.username = username;
        this.password = password;
    }
}
