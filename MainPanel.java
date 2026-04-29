import java.awt.*;
import javax.swing.*;

public class MainPanel extends JPanel {

    private CardLayout layout;
    private JPanel     container;

    DashboardPanel       dashboard;
    AttendanceInputPanel attendance;
    ProfilePanel         profile;

    private final StudentDashboard frame;

    public MainPanel(StudentDashboard frame) {
        this.frame = frame;

        layout    = new CardLayout();
        container = new JPanel(layout);

        dashboard  = new DashboardPanel();
        attendance = new AttendanceInputPanel();  
        profile    = new ProfilePanel();

        dashboard.setPreferredSize(new Dimension(0, 900));
        profile.setPreferredSize(new Dimension(0, 900));
        attendance.setPreferredSize(new Dimension(0, 760));

        container.add(dashboard,  "dashboard");
        container.add(attendance, "attendance");
        container.add(profile,    "profile");
        container.setPreferredSize(new Dimension(0, 900));

        setLayout(new BorderLayout());
        JScrollPane mainScrollPane = new JScrollPane(container);
        mainScrollPane.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED);
        mainScrollPane.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
        mainScrollPane.setBorder(BorderFactory.createEmptyBorder());
        mainScrollPane.getVerticalScrollBar().setUnitIncrement(16);
        add(mainScrollPane, BorderLayout.CENTER);
    }

    public void showPanel(String name) {
        if ("profile".equals(name)) {
            profile.refreshProfile();
        }
        container.setPreferredSize(new Dimension(0, "attendance".equals(name) ? 760 : 900));
        container.revalidate();
        layout.show(container, name);
        frame.showRightPanel(name.equals("attendance"));
    }
}
