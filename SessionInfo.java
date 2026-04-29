import java.io.Serializable;
import java.time.LocalDate;

public class SessionInfo implements Serializable {

    private static final long serialVersionUID = 1L;

    private final LocalDate startDate;
    private final LocalDate endDate;

    public SessionInfo(LocalDate startDate, LocalDate endDate) {
        if (startDate == null || endDate == null)
            throw new IllegalArgumentException("Session dates cannot be null");
        if (!endDate.isAfter(startDate))
            throw new IllegalArgumentException("End date must be after start date");

        this.startDate = startDate;
        this.endDate   = endDate;
    }

    public LocalDate getStartDate() { return startDate; }
    public LocalDate getEndDate()   { return endDate; }

    public boolean contains(LocalDate date) {
        return !date.isBefore(startDate) && !date.isAfter(endDate);
    }

    @Override
    public String toString() {
        return startDate + " → " + endDate;
    }
}
