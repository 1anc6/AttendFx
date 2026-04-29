import java.awt.*;
import javax.swing.*;

public class StudentDashboard extends JFrame {

    private final RightPanel right;
    private final MainPanel  main;
    private final JScrollPane rightScroll;

    public StudentDashboard(String username) {
        setTitle("Student Dashboard");
        setSize(1200, 700);
        setLocationRelativeTo(null);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);

        right = new RightPanel();
        main  = new MainPanel(this);

        SidebarPanel sidebar = new SidebarPanel(main);
        JScrollPane sidebarScroll = new JScrollPane(sidebar);
        sidebarScroll.setPreferredSize(new Dimension(220, 0));
        sidebarScroll.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED);
        sidebarScroll.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
        sidebarScroll.setBorder(BorderFactory.createEmptyBorder());
        sidebarScroll.getViewport().setBackground(new Color(15, 35, 120));
        sidebarScroll.getVerticalScrollBar().setUnitIncrement(16);

        rightScroll = new JScrollPane(right);
        rightScroll.setPreferredSize(new Dimension(290, 0));
        rightScroll.setVerticalScrollBarPolicy(JScrollPane.VERTICAL_SCROLLBAR_AS_NEEDED);
        rightScroll.setHorizontalScrollBarPolicy(JScrollPane.HORIZONTAL_SCROLLBAR_NEVER);
        rightScroll.setBorder(BorderFactory.createEmptyBorder());
        rightScroll.getViewport().setBackground(new Color(245, 247, 251));
        rightScroll.getVerticalScrollBar().setUnitIncrement(16);

        add(sidebarScroll,          BorderLayout.WEST);
        add(main,                   BorderLayout.CENTER);
        add(rightScroll,            BorderLayout.EAST);

        setVisible(true);

        SwingUtilities.invokeLater(() ->
            AttendanceService.getInstance().notifyDataLoaded()
        );
    }

    public void showRightPanel(boolean show) {
        rightScroll.setVisible(show);
        revalidate();
        repaint();
    }
}
