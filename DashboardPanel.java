import java.awt.*;
import java.time.LocalDate;
import java.util.*;
import java.util.List;
import javax.swing.*;

public class DashboardPanel extends JPanel implements AttendanceChangeListener {

    private static final Color SAFE_COLOR     = new Color(0,  200,  0);
    private static final Color WARNING_COLOR  = Color.ORANGE;
    private static final Color CRITICAL_COLOR = Color.RED;
    private static final Color BG_COLOR       = new Color(240, 242, 245);
    private static final Font  FONT_LG = new Font("Segoe UI", Font.BOLD, 24);
    private static final Font  FONT_MD = new Font("Segoe UI", Font.BOLD, 18);

    private JLabel attendanceValue;
    private JLabel profileLabel;
    private JLabel overallLabel;
    private JLabel neededLabel;
    private JLabel absenceLabel;
    private JLabel attendedCountLabel;  
    private JLabel absentCountLabel;    
    private JLabel predictionLabel;
    private JLabel workingDaysLabel;

    private final List<Double> history = new ArrayList<>();
    private GraphPanel graphPanel;

    private final AttendanceService service = AttendanceService.getInstance();

    public DashboardPanel() {
        service.addListener(this);
        setLayout(new BorderLayout(20, 20));
        setBackground(BG_COLOR);
        add(buildTopPanel(),    BorderLayout.NORTH);
        add(buildCenterPanel(), BorderLayout.CENTER);
    }

    private JPanel buildTopPanel() {
        JPanel panel = new JPanel(new GridLayout(1, 3, 20, 20));
        panel.setBackground(BG_COLOR);
        panel.add(buildStudentProfileCard());
        panel.add(buildAttendanceCard());
        panel.add(buildWorkingDaysCard());
        return panel;
    }

    private JPanel buildCenterPanel() {
        JPanel panel = new JPanel(new GridLayout(1, 2, 20, 20));
        panel.setBackground(BG_COLOR);
        panel.add(buildGraphCard());
        panel.add(buildSummaryPanel());
        return panel;
    }

    private JPanel staticCard(String title, String value) {
        RoundedPanel p = new RoundedPanel(20, Color.WHITE);
        p.setLayout(new BorderLayout());
        p.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
        JLabel v = new JLabel(value);
        v.setFont(FONT_MD);
        p.add(new JLabel(title), BorderLayout.NORTH);
        p.add(v, BorderLayout.CENTER);
        return wrapShadow(p);
    }

    private JPanel buildStudentProfileCard() {
        RoundedPanel p = new RoundedPanel(20, Color.WHITE);
        p.setLayout(new BorderLayout());
        p.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
        profileLabel = new JLabel("Student");
        profileLabel.setFont(new Font("Segoe UI", Font.PLAIN, 12));
        p.add(new JLabel("Student"), BorderLayout.NORTH);
        p.add(profileLabel, BorderLayout.CENTER);
        return wrapShadow(p);
    }

    private JPanel buildWorkingDaysCard() {
        RoundedPanel p = new RoundedPanel(20, Color.WHITE);
        p.setLayout(new BorderLayout());
        p.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
        workingDaysLabel = new JLabel("0");
        workingDaysLabel.setFont(FONT_MD);
        p.add(new JLabel("Working Days"), BorderLayout.NORTH);
        p.add(workingDaysLabel, BorderLayout.CENTER);
        return wrapShadow(p);
    }

    private JPanel buildAttendanceCard() {
        RoundedPanel p = new RoundedPanel(20, Color.WHITE);
        p.setLayout(new BorderLayout());
        p.setBorder(BorderFactory.createEmptyBorder(15, 15, 15, 15));
        attendanceValue = new JLabel("0%");
        attendanceValue.setFont(FONT_LG);
        p.add(new JLabel("Attendance Rate"), BorderLayout.NORTH);
        p.add(attendanceValue, BorderLayout.CENTER);
        return wrapShadow(p);
    }

    private JPanel buildGraphCard() {
        RoundedPanel p = new RoundedPanel(20, Color.WHITE);
        p.setLayout(new BorderLayout());
        p.setBorder(BorderFactory.createTitledBorder("Attendance Trend"));
        graphPanel = new GraphPanel(history, service);
        p.add(graphPanel, BorderLayout.CENTER);
        return wrapShadow(p);
    }

    private JPanel buildSummaryPanel() {
        overallLabel       = boldLabel("0%");
        neededLabel        = boldLabel("0");
        absenceLabel       = boldLabel("0");
        attendedCountLabel = boldLabel("0");   
        absentCountLabel   = boldLabel("0");   
        predictionLabel    = boldLabel("0");

        JPanel panel = new JPanel(new GridLayout(6, 1, 10, 10));
        panel.setBackground(BG_COLOR);
        panel.add(summaryBox("Overall Attendance",   overallLabel));
        panel.add(summaryBox("Classes Needed",       neededLabel));
        panel.add(summaryBox("Allowable Absences",   absenceLabel));
        panel.add(summaryBox("Classes Attended",     attendedCountLabel));  
        panel.add(summaryBox("Classes Absent",       absentCountLabel));    
        panel.add(summaryBox("Can Miss Safely",      predictionLabel));
        return panel;
    }

    private JLabel boldLabel(String text) {
        JLabel l = new JLabel(text);
        l.setFont(FONT_MD);
        return l;
    }

    private JPanel summaryBox(String title, JLabel valueLabel) {
        RoundedPanel p = new RoundedPanel(20, Color.WHITE);
        p.setLayout(new BorderLayout());
        p.setBorder(BorderFactory.createEmptyBorder(10, 15, 10, 15));
        JLabel titleLbl = new JLabel(title);
        titleLbl.setFont(new Font("Segoe UI", Font.PLAIN, 12));
        p.add(titleLbl,   BorderLayout.NORTH);
        p.add(valueLabel, BorderLayout.CENTER);
        return wrapShadow(p);
    }

    private JPanel wrapShadow(JPanel panel) {
        ShadowPanel shadow = new ShadowPanel(new BorderLayout());
        shadow.add(panel, BorderLayout.CENTER);
        return shadow;
    }

    static Color statusColor(double percent) {
        if (percent >= AttendanceService.REQUIRED_PCT) return SAFE_COLOR;
        if (percent >= AttendanceService.WARNING_PCT)  return WARNING_COLOR;
        return CRITICAL_COLOR;
    }

    public void updateAttendance(double percent) {
        attendanceValue.setText(String.format("%.2f%%", percent));
        attendanceValue.setForeground(statusColor(percent));
        overallLabel.setText(String.format("%.2f%%", percent));
        overallLabel.setForeground(statusColor(percent));
    }

    public void updateGraph(double percent) {
        history.add(percent);
        graphPanel.resetAnimation();
        graphPanel.repaint();
    }

    public void updateNeeded(int needed) {
        neededLabel.setText(String.valueOf(needed));
    }

    public void updateAbsence(int absence) {
        absenceLabel.setText(String.valueOf(absence));
    }

    private void updateCounts() {
        int attended = service.getTotalAttended();
        int absent   = service.getTotalAbsent();
        attendedCountLabel.setText(String.valueOf(attended));
        absentCountLabel.setText(String.valueOf(absent));
        absentCountLabel.setForeground(absent > 0 ? Color.RED : Color.BLACK);
        predictionLabel.setText(String.valueOf(service.getSafeMissableClasses()));
    }

    private void updateWorkingDays() {
        workingDaysLabel.setText(String.valueOf(service.getTotalWorkingDaysInSession()));
    }

    private void updateStudentProfile() {
        StudentRecord student = service.getCurrentStudentProfile();
        if (student == null) {
            profileLabel.setText("<html><b>Student</b></html>");
            return;
        }

        profileLabel.setText("<html><b>" + safe(student.name) + "</b></html>");
    }

    private String safe(String value) {
        return value == null || value.trim().isEmpty() ? "N/A" : value.trim();
    }

    @Override
    public void onDataLoaded() {
        SwingUtilities.invokeLater(() -> {
            double pct = service.getOverallAttendance();

            history.clear();
            if (pct > 0) { history.add(pct); history.add(pct); }
            updateAttendance(pct);
            updateNeeded(service.getTotalNeeded());
            updateAbsence(service.getTotalAllowable());
            updateCounts();
            updateWorkingDays();
            updateStudentProfile();
            graphPanel.repaint();
        });
    }

    @Override
    public void onSessionChanged(SessionInfo session) {
        SwingUtilities.invokeLater(this::updateWorkingDays);
    }

    @Override
    public void onSubjectAdded(Subject subject) {
        SwingUtilities.invokeLater(() -> {
            double pct = service.getOverallAttendance();
            updateAttendance(pct);
            updateGraph(pct);
            updateNeeded(service.getTotalNeeded());
            updateAbsence(service.getTotalAllowable());
            updateCounts();  
        });
    }

    @Override
    public void onDailyAttendanceChanged(LocalDate date, Boolean attended) {  }

    private static class GraphPanel extends JPanel {

        private static final int   PADDING      = 40;
        private static final int   STEP_X       = 60;
        private static final int   Y_SCALE      = 2;   
        private static final float STROKE_WIDTH = 3f;

        private static final int[] GRID_LEVELS = {25, 50, 75, 100};

        private final List<Double> history;
        private final AttendanceService service;
        private int animationProgress = 0;
        private final javax.swing.Timer timer;

        GraphPanel(List<Double> history, AttendanceService service) {
            this.history = history;
            this.service = service;
            setBackground(Color.WHITE);

            timer = new javax.swing.Timer(20, e -> {
                animationProgress += 5;
                int target = history.isEmpty() ? 0 : history.size() * 10;
                if (animationProgress >= target) {
                    animationProgress = target;
                    ((javax.swing.Timer) e.getSource()).stop();
                }
                repaint();
            });
            timer.start();
        }

        void resetAnimation() {
            animationProgress = 0;
            timer.restart();
        }

        @Override
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);

            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);

            int h = getHeight();

            g2.setStroke(new BasicStroke(0.8f, BasicStroke.CAP_BUTT,
                BasicStroke.JOIN_MITER, 10f, new float[]{4f, 4f}, 0f));

            for (int level : GRID_LEVELS) {
                int y = h - PADDING - (level * Y_SCALE);
                if (y < 0) continue;

                if (level == 75) g2.setColor(new Color(0, 200, 0, 80));
                else if (level == 65) g2.setColor(new Color(255, 165, 0, 80));
                else g2.setColor(new Color(180, 180, 180, 120));

                g2.drawLine(PADDING, y, getWidth() - 10, y);

                g2.setColor(new Color(120, 120, 120));
                g2.setFont(new Font("Segoe UI", Font.PLAIN, 9));
                g2.drawString(level + "%", 2, y + 4);
            }

            int y75 = h - PADDING - (75 * Y_SCALE);
            if (y75 >= 0) {
                g2.setStroke(new BasicStroke(1.2f));
                g2.setColor(new Color(0, 180, 0, 150));
                g2.drawLine(PADDING, y75, getWidth() - 10, y75);
                g2.setFont(new Font("Segoe UI", Font.BOLD, 9));
                g2.setColor(new Color(0, 140, 0));
                g2.drawString("Min 75%", 2, y75 - 2);
            }

            int attended = service.getTotalAttended();
            int absent = service.getTotalAbsent();
            int total = attended + absent;
            double attendedPct = total == 0 ? 0.0 : (attended * 100.0) / total;
            double absentPct = total == 0 ? 0.0 : (absent * 100.0) / total;
            int baseY = h - PADDING;
            int barWidth = 55;
            int attendedHeight = (int) (attendedPct * Y_SCALE);
            int absentHeight = (int) (absentPct * Y_SCALE);

            g2.setFont(new Font("Segoe UI", Font.BOLD, 11));
            g2.setColor(new Color(0, 160, 80));
            g2.fillRect(PADDING + 80, baseY - attendedHeight, barWidth, attendedHeight);
            g2.drawString(String.format("Attended: %d (%.1f%%)", attended, attendedPct), PADDING + 45, baseY + 18);

            g2.setColor(new Color(220, 70, 70));
            g2.fillRect(PADDING + 190, baseY - absentHeight, barWidth, absentHeight);
            g2.drawString(String.format("Absent: %d (%.1f%%)", absent, absentPct), PADDING + 170, baseY + 18);

            if (attended > 0 || absent > 0) {
                g2.dispose();
                return;
            }

            if (history.size() < 2) {
                g2.dispose();
                return;
            }

            g2.setStroke(new BasicStroke(STROKE_WIDTH));
            int limit = Math.min(animationProgress / 10, history.size());

            for (int i = 0; i < limit - 1; i++) {
                double v1 = history.get(i);
                double v2 = history.get(i + 1);
                g2.setColor(statusColor(v2));
                g2.drawLine(
                    PADDING + i * STEP_X,
                    h - PADDING - (int) (v1 * Y_SCALE),
                    PADDING + (i + 1) * STEP_X,
                    h - PADDING - (int) (v2 * Y_SCALE)
                );

                g2.fillOval(
                    PADDING + (i + 1) * STEP_X - 4,
                    h - PADDING - (int) (v2 * Y_SCALE) - 4,
                    8, 8
                );
            }

            if (limit > 0) {
                double last = history.get(limit - 1);
                int lx = PADDING + (limit - 1) * STEP_X;
                int ly = h - PADDING - (int) (last * Y_SCALE);
                g2.setFont(new Font("Segoe UI", Font.BOLD, 10));
                g2.setColor(statusColor(last));
                g2.drawString(String.format("%.1f%%", last), lx + 5, ly - 5);
            }

            g2.dispose();
        }
    }
}
