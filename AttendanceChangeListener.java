import java.time.LocalDate;

public interface AttendanceChangeListener {

    void onDataLoaded();

    void onSessionChanged(SessionInfo session);

    void onSubjectAdded(Subject subject);

    void onDailyAttendanceChanged(LocalDate date, Boolean attended);

    default void onTeacherDataChanged() {  }
}
