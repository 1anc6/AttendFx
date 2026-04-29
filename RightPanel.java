import java.awt.*;
import java.awt.event.*;
import java.time.*;
import java.time.format.TextStyle;
import java.util.*;
import javax.swing.*;
import javax.swing.border.EmptyBorder;

public class RightPanel extends JPanel implements AttendanceChangeListener {

    private static final Color COLOR_ATTENDED     = new Color(108, 214, 141);
    private static final Color COLOR_ABSENT       = new Color(245, 110, 110);
    private static final Color COLOR_NOT_MARKED   = Color.WHITE;
    private static final Color COLOR_SUNDAY       = new Color(232, 235, 243);
    private static final Color COLOR_OUT_SESSION  = new Color(243, 245, 250);
    private static final Color COLOR_HEADER_BG    = new Color(26, 42, 112);
    private static final Color COLOR_HEADER_FG    = Color.WHITE;
    private static final Color COLOR_BORDER       = new Color(219, 226, 239);
    private static final Color COLOR_TODAY        = new Color(44, 103, 242);
    private static final Color COLOR_PANEL_BG     = new Color(245, 247, 251);
    private static final Color COLOR_TEXT_PRIMARY = new Color(31, 42, 67);
    private static final Color COLOR_TEXT_MUTED   = new Color(104, 116, 145);

    private YearMonth            displayMonth;
    private SessionInfo          session;
    private final AttendanceService service = AttendanceService.getInstance();

    private JLabel   monthLabel;
    private JButton  prevBtn, nextBtn;
    private JPanel   dayGrid;              
    private JPanel calendarWrapper;
    private JLabel weekInsightLabel;

    private SummaryCard overallCard;
    private SummaryCard neededCard;
    private SummaryCard absenceCard;

    public RightPanel() {
        service.addListener(this);

        setPreferredSize(new Dimension(290, 760));
        setMinimumSize(new Dimension(290, 760));
        setBackground(COLOR_PANEL_BG);
        setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));
        setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

        JPanel calendarPanel = createCalendarPanel();
        JPanel cardsPanel = createCards();
        calendarPanel.setAlignmentX(Component.LEFT_ALIGNMENT);
        cardsPanel.setAlignmentX(Component.LEFT_ALIGNMENT);
        calendarPanel.setMaximumSize(new Dimension(Integer.MAX_VALUE, calendarPanel.getPreferredSize().height));

        add(calendarPanel);
        add(Box.createRigidArea(new Dimension(0, 10)));
        add(cardsPanel);
        add(Box.createRigidArea(new Dimension(0, 20)));

        displayMonth = YearMonth.now();
        renderCalendar();
    }

    private JPanel createCalendarPanel() {
        calendarWrapper = new RoundedPanel(24, Color.WHITE);
        calendarWrapper.setLayout(new BorderLayout(6, 6));
        calendarWrapper.setBackground(Color.WHITE);
        calendarWrapper.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createTitledBorder(
                BorderFactory.createLineBorder(COLOR_BORDER, 1, true),
                "Calendar"
            ),
            BorderFactory.createEmptyBorder(6, 6, 6, 6)
        ));

        JPanel nav = new JPanel(new BorderLayout());
        nav.setBackground(COLOR_HEADER_BG);
        nav.setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 10));

        prevBtn    = navButton("◀");
        nextBtn    = navButton("▶");
        monthLabel = new JLabel("", SwingConstants.CENTER);
        monthLabel.setForeground(COLOR_HEADER_FG);
        monthLabel.setFont(new Font("Segoe UI", Font.BOLD, 12));

        prevBtn.addActionListener(e -> navigateMonth(-1));
        nextBtn.addActionListener(e -> navigateMonth(+1));

        nav.add(prevBtn,    BorderLayout.WEST);
        nav.add(monthLabel, BorderLayout.CENTER);
        nav.add(nextBtn,    BorderLayout.EAST);

        JPanel dowHeader = new JPanel(new GridLayout(1, 7, 0, 0));
        dowHeader.setBackground(new Color(236, 241, 252));
        String[] dowNames = {"S","M","T","W","T","F","S"};
        for (String d : dowNames) {
            JLabel lbl = new JLabel(d, SwingConstants.CENTER);
            lbl.setFont(new Font("Segoe UI", Font.BOLD, 12));
            lbl.setForeground(new Color(57, 76, 126));
            lbl.setBorder(BorderFactory.createEmptyBorder(6, 0, 6, 0));
            dowHeader.add(lbl);
        }

        dayGrid = new JPanel(new GridLayout(0, 7, 4, 4));
        dayGrid.setBackground(new Color(235, 239, 247));
        dayGrid.setBorder(BorderFactory.createEmptyBorder(6, 0, 0, 0));

        JPanel calBody = new JPanel(new BorderLayout(0, 2));
        calBody.setBackground(Color.WHITE);
        calBody.setBorder(BorderFactory.createEmptyBorder(0, 4, 4, 4));
        calBody.add(dowHeader, BorderLayout.NORTH);
        calBody.add(dayGrid,   BorderLayout.CENTER);

        calendarWrapper.add(nav,     BorderLayout.NORTH);
        calendarWrapper.add(calBody, BorderLayout.CENTER);

        JPanel footer = new JPanel();
        footer.setLayout(new BoxLayout(footer, BoxLayout.Y_AXIS));
        footer.setBackground(Color.WHITE);
        footer.add(createLegend());
        weekInsightLabel = new JLabel("This week: no marks yet");
        weekInsightLabel.setFont(new Font("Segoe UI", Font.BOLD, 11));
        weekInsightLabel.setForeground(COLOR_TEXT_PRIMARY);
        weekInsightLabel.setBorder(BorderFactory.createEmptyBorder(3, 4, 2, 4));
        footer.add(weekInsightLabel);
        calendarWrapper.add(footer, BorderLayout.SOUTH);

        return calendarWrapper;
    }

    private void renderCalendar() {
        dayGrid.removeAll();

        monthLabel.setText(
            displayMonth.getMonth().getDisplayName(TextStyle.SHORT, Locale.ENGLISH)
            + " " + displayMonth.getYear()
        );
        if (session != null) {
            calendarWrapper.setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createTitledBorder(
                    BorderFactory.createLineBorder(COLOR_BORDER, 1, true),
                    "Calendar: " + session.getStartDate() + " to " + session.getEndDate()
                ),
                BorderFactory.createEmptyBorder(6, 6, 6, 6)
            ));
        }

        LocalDate first = displayMonth.atDay(1);
        int startDow = first.getDayOfWeek().getValue() % 7; 

        for (int i = 0; i < startDow; i++) {
            dayGrid.add(emptyCell());
        }

        int daysInMonth = displayMonth.lengthOfMonth();
        for (int d = 1; d <= daysInMonth; d++) {
            LocalDate date = displayMonth.atDay(d);
            dayGrid.add(createDayCell(date));
        }

        dayGrid.revalidate();
        dayGrid.repaint();

        updateWeekInsight();
        updateNavButtons();
    }

    private JPanel createDayCell(LocalDate date) {
        boolean isSunday    = date.getDayOfWeek() == DayOfWeek.SUNDAY;
        boolean inSession   = (session != null) && session.contains(date);
        Boolean attendance  = service.getCalendarAttendanceStatus(date);
        boolean isToday     = date.equals(LocalDate.now());
        boolean inCurrentWeek = isCurrentWeek(date);

        Color bg;
        if      (!inSession)           bg = COLOR_OUT_SESSION;
        else if (isSunday)             bg = COLOR_SUNDAY;
        else if (attendance == null)   bg = COLOR_SUNDAY;
        else if (attendance)           bg = COLOR_ATTENDED;
        else                           bg = COLOR_ABSENT;

        JPanel cell = new JPanel(new BorderLayout());
        cell.setBackground(bg);
        cell.setOpaque(true);
        cell.setPreferredSize(new Dimension(34, 34));
        cell.setBorder(BorderFactory.createLineBorder(new Color(225, 231, 242), 1, true));
        cell.setToolTipText(attendanceTooltip(date, inSession, isSunday, attendance));

        JLabel lbl = new JLabel(String.valueOf(date.getDayOfMonth()), SwingConstants.CENTER);
        lbl.setFont(new Font("Segoe UI", isToday ? Font.BOLD : Font.PLAIN, 12));
        lbl.setForeground(inSession && !isSunday ? COLOR_TEXT_PRIMARY : new Color(160, 160, 160));
        cell.add(lbl, BorderLayout.CENTER);

        if (isToday) {
            cell.setBorder(BorderFactory.createLineBorder(COLOR_TODAY, 2, true));
            lbl.setForeground(COLOR_TODAY.darker());
        } else if (inCurrentWeek && inSession) {
            cell.setBorder(BorderFactory.createLineBorder(new Color(125, 150, 230), 2, true));
        }

        if (inSession && !isSunday) {
            cell.addMouseListener(new MouseAdapter() {
                @Override public void mouseEntered(MouseEvent e) {
                    cell.setBorder(BorderFactory.createLineBorder(new Color(15, 35, 120), isToday ? 2 : 1, true));
                }
                @Override public void mouseExited(MouseEvent e) {
                    cell.setBorder(BorderFactory.createLineBorder(
                        isToday ? COLOR_TODAY : new Color(225, 231, 242),
                        isToday || inCurrentWeek ? 2 : 1,
                        true
                    ));
                }
            });
        }

        return cell;
    }

    private JPanel emptyCell() {
        JPanel p = new JPanel();
        p.setBackground(COLOR_PANEL_BG);
        p.setOpaque(true);
        return p;
    }

    private JPanel createLegend() {
        JPanel legend = new JPanel(new FlowLayout(FlowLayout.LEFT, 4, 2));
        legend.setBackground(Color.WHITE);
        legend.add(legendDot(COLOR_ATTENDED,   "Attended"));
        legend.add(legendDot(COLOR_ABSENT,     "Absent"));
        legend.add(legendDot(COLOR_SUNDAY,     "No class"));
        return legend;
    }

    private JPanel legendDot(Color color, String label) {
        JPanel p = new JPanel(new FlowLayout(FlowLayout.LEFT, 2, 0));
        p.setOpaque(false);
        JPanel dot = new JPanel();
        dot.setPreferredSize(new Dimension(12, 12));
        dot.setBackground(color);
        dot.setOpaque(true);
        JLabel lbl = new JLabel(label);
        lbl.setFont(new Font("Segoe UI", Font.PLAIN, 10));
        lbl.setForeground(COLOR_TEXT_PRIMARY);
        p.add(dot); p.add(lbl);
        return p;
    }

    private JButton navButton(String text) {
        JButton btn = new JButton(text);
        btn.setForeground(COLOR_HEADER_FG);
        btn.setBackground(COLOR_HEADER_BG);
        btn.setFocusPainted(false);
        btn.setBorderPainted(false);
        btn.setFont(new Font("Segoe UI Symbol", Font.BOLD, 12));
        btn.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        btn.setContentAreaFilled(false);
        btn.setOpaque(false);
        return btn;
    }

    private void navigateMonth(int delta) {
        YearMonth candidate = displayMonth.plusMonths(delta);

        if (session != null) {
            YearMonth sessionStart = YearMonth.from(session.getStartDate());
            YearMonth sessionEnd   = YearMonth.from(session.getEndDate());
            if (candidate.isBefore(sessionStart) || candidate.isAfter(sessionEnd)) return;
        }

        displayMonth = candidate;
        renderCalendar();
    }

    private void updateNavButtons() {
        if (session == null) { prevBtn.setEnabled(false); nextBtn.setEnabled(false); return; }
        YearMonth sessionStart = YearMonth.from(session.getStartDate());
        YearMonth sessionEnd   = YearMonth.from(session.getEndDate());
        prevBtn.setEnabled(!displayMonth.equals(sessionStart));
        nextBtn.setEnabled(!displayMonth.equals(sessionEnd));
    }

    private JPanel createCards() {
        JPanel p = new JPanel();
        p.setLayout(new BoxLayout(p, BoxLayout.Y_AXIS));
        p.setBackground(COLOR_PANEL_BG);

        overallCard = new SummaryCard(
            "\uD83D\uDCCA",
            "Overall Attendance",
            "0.00%",
            "SAFE",
            new Color(255, 247, 204)
        );
        neededCard = new SummaryCard(
            "\uD83D\uDCC8",
            "Classes Needed",
            "0",
            "",
            new Color(214, 246, 228)
        );
        absenceCard = new SummaryCard(
            "\u274C",
            "Allowable Absences",
            "0",
            "",
            new Color(255, 225, 225)
        );

        Dimension cardSize = new Dimension(270, 126);
        applyCardSize(overallCard, cardSize);
        applyCardSize(neededCard, cardSize);
        applyCardSize(absenceCard, cardSize);

        p.add(overallCard);
        p.add(Box.createRigidArea(new Dimension(0, 10)));
        p.add(neededCard);
        p.add(Box.createRigidArea(new Dimension(0, 10)));
        p.add(absenceCard);
        p.add(Box.createVerticalGlue());
        return p;
    }

    private void applyCardSize(JComponent card, Dimension size) {
        card.setPreferredSize(size);
        card.setMinimumSize(size);
        card.setMaximumSize(new Dimension(Integer.MAX_VALUE, size.height));
        card.setAlignmentX(Component.LEFT_ALIGNMENT);
    }

    public void updateOverall(double percent) {
        String status = service.getStatusLabel(percent);
        overallCard.setValue(String.format("%.2f%%", percent));
        overallCard.setStatus(status);
        overallCard.setProgress(percent);
    }

    public void updateNeeded(int needed) {
        neededCard.setValue(String.valueOf(needed));
    }

    public void updateAbsence(int abs) {
        absenceCard.setValue(String.valueOf(abs));
    }

    @Override
    public void onDataLoaded() {
        SwingUtilities.invokeLater(() -> {
            updateOverall(service.getOverallAttendance());
            updateNeeded(service.getTotalNeeded());
            updateAbsence(service.getTotalAllowable());
            renderCalendar();
        });
    }

    @Override
    public void onSessionChanged(SessionInfo sess) {
        this.session     = sess;
        this.displayMonth = YearMonth.from(sess.getStartDate());
        SwingUtilities.invokeLater(this::renderCalendar);
    }

    @Override
    public void onSubjectAdded(Subject subject) {
        SwingUtilities.invokeLater(() -> {
            updateOverall(service.getOverallAttendance());
            updateNeeded(service.getTotalNeeded());
            updateAbsence(service.getTotalAllowable());
        });
    }

    @Override
    public void onDailyAttendanceChanged(LocalDate date, Boolean attended) {

        SwingUtilities.invokeLater(this::renderCalendar);
    }

    private String attendanceTooltip(LocalDate date, boolean inSession, boolean isSunday, Boolean attendance) {
        String status;
        if (!inSession || isSunday) status = "No class";
        else if (attendance == null) status = "No class";
        else status = attendance ? "Present" : "Absent";
        StringBuilder tip = new StringBuilder("<html>Date: ")
            .append(date)
            .append("<br>Status: ")
            .append(status)
            .append("<br>Classes: ")
            .append(classCountFor(date, inSession, isSunday));
        java.util.Map<String, String> details = service.getCalendarSubjectStatuses(date);
        if (!details.isEmpty()) {
            tip.append("<br>");
            for (java.util.Map.Entry<String, String> entry : details.entrySet()) {
                tip.append("<br>").append(entry.getKey()).append(": ").append(entry.getValue());
            }
        }
        return tip.append("</html>").toString();
    }

    private int classCountFor(LocalDate date, boolean inSession, boolean isSunday) {
        if (!inSession || isSunday) return 0;
        return service.getCalendarClassCount(date);
    }

    private boolean isCurrentWeek(LocalDate date) {
        LocalDate today = LocalDate.now();
        LocalDate start = today.minusDays(today.getDayOfWeek().getValue() % 7);
        LocalDate end = start.plusDays(6);
        return !date.isBefore(start) && !date.isAfter(end);
    }

    private void updateWeekInsight() {
        if (weekInsightLabel == null) return;
        LocalDate today = LocalDate.now();
        LocalDate start = today.minusDays(today.getDayOfWeek().getValue() % 7);
        int present = 0;
        int absent = 0;
        for (int i = 0; i < 7; i++) {
            LocalDate date = start.plusDays(i);
            if (session == null || !session.contains(date) || date.getDayOfWeek() == DayOfWeek.SUNDAY) continue;
            Boolean status = service.getCalendarAttendanceStatus(date);
            if (Boolean.TRUE.equals(status)) present++;
            else if (Boolean.FALSE.equals(status)) absent++;
        }
        int marked = present + absent;
        if (marked == 0) {
            weekInsightLabel.setText("This week: no generated classes");
            return;
        }
        int pct = (int) Math.round((present * 100.0) / marked);
        weekInsightLabel.setText("This week: " + pct + "% attendance (" + absent + " missed)");
    }

    private class SummaryCard extends RoundedPanel {
        private final JLabel iconLabel;
        private final JLabel titleLabel;
        private final JLabel valueLabel;
        private final PillBadge statusBadge;
        private final ProgressBar progressBar;

        SummaryCard(String icon, String title, String value, String status, Color background) {
            super(24, background);
            setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));
            setBorder(new EmptyBorder(16, 16, 16, 16));

            JPanel top = new JPanel(new BorderLayout(8, 0));
            top.setOpaque(false);
            top.setAlignmentX(Component.LEFT_ALIGNMENT);
            top.setMaximumSize(new Dimension(Integer.MAX_VALUE, 34));

            iconLabel = new JLabel(icon);
            iconLabel.setFont(new Font("Segoe UI Emoji", Font.PLAIN, 20));
            titleLabel = new JLabel(title);
            titleLabel.setFont(new Font("Segoe UI", Font.BOLD, 14));
            titleLabel.setForeground(COLOR_TEXT_PRIMARY);
            titleLabel.setAlignmentX(Component.LEFT_ALIGNMENT);

            JPanel titleWrap = new JPanel();
            titleWrap.setLayout(new BoxLayout(titleWrap, BoxLayout.Y_AXIS));
            titleWrap.setOpaque(false);
            titleWrap.add(titleLabel);

            statusBadge = new PillBadge();
            statusBadge.setVisible(!status.isEmpty());
            statusBadge.setAlignmentX(Component.LEFT_ALIGNMENT);
            titleWrap.add(Box.createRigidArea(new Dimension(0, 4)));
            titleWrap.add(statusBadge);

            top.add(iconLabel, BorderLayout.WEST);
            top.add(titleWrap, BorderLayout.CENTER);

            valueLabel = new JLabel(value);
            valueLabel.setFont(new Font("Segoe UI", Font.BOLD, 18));
            valueLabel.setForeground(COLOR_TEXT_PRIMARY);
            valueLabel.setAlignmentX(Component.LEFT_ALIGNMENT);

            progressBar = new ProgressBar();
            progressBar.setVisible(false);
            progressBar.setAlignmentX(Component.LEFT_ALIGNMENT);
            progressBar.setMaximumSize(new Dimension(Integer.MAX_VALUE, 12));

            add(top);
            add(Box.createRigidArea(new Dimension(0, 8)));
            add(valueLabel);
            add(Box.createRigidArea(new Dimension(0, 8)));
            add(progressBar);

            setStatus(status);
        }

        void setValue(String value) {
            valueLabel.setText(value);
            valueLabel.setFont(value.contains("%")
                ? new Font("Segoe UI", Font.BOLD, 20)
                : new Font("Segoe UI", Font.BOLD, 18));
        }

        void setStatus(String status) {
            if (status == null || status.trim().isEmpty()) {
                statusBadge.setVisible(false);
                return;
            }
            String normalized = status.toUpperCase(Locale.ENGLISH);
            statusBadge.setVisible(true);
            statusBadge.setText(normalized);
            if (normalized.contains("CRITICAL")) {
                statusBadge.setBackground(new Color(220, 73, 73));
            } else if (normalized.contains("WARNING") || normalized.contains("POSSIBLE")) {
                statusBadge.setBackground(new Color(226, 182, 63));
            } else {
                statusBadge.setBackground(new Color(89, 169, 98));
            }
        }

        void setProgress(double percent) {
            progressBar.setVisible(true);
            progressBar.setValue(percent);
        }
    }

    private static class PillBadge extends JLabel {
        PillBadge() {
            setOpaque(false);
            setFont(new Font("Segoe UI", Font.BOLD, 11));
            setForeground(Color.WHITE);
            setBorder(new EmptyBorder(4, 10, 4, 10));
        }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g2.setColor(getBackground());
            g2.fillRoundRect(0, 0, getWidth(), getHeight(), getHeight(), getHeight());
            g2.dispose();
            super.paintComponent(g);
        }
    }

    private static class ProgressBar extends JComponent {
        private double value;

        ProgressBar() {
            setPreferredSize(new Dimension(200, 12));
            setMinimumSize(new Dimension(120, 12));
            setMaximumSize(new Dimension(Integer.MAX_VALUE, 12));
        }

        void setValue(double value) {
            this.value = Math.max(0, Math.min(100, value));
            repaint();
        }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            int width = getWidth();
            int height = getHeight();
            g2.setColor(new Color(255, 255, 255, 140));
            g2.fillRoundRect(0, 0, width, height, height, height);

            Color fill = value > 75 ? new Color(89, 169, 98)
                : value >= 60 ? new Color(226, 182, 63)
                : new Color(220, 73, 73);
            int fillWidth = (int) Math.round(width * (value / 100.0));
            g2.setColor(fill);
            g2.fillRoundRect(0, 0, fillWidth, height, height, height);

            g2.setColor(COLOR_TEXT_MUTED);
            g2.setFont(new Font("Segoe UI", Font.BOLD, 10));
            String text = String.format("%.0f%%", value);
            FontMetrics fm = g2.getFontMetrics();
            int textX = Math.max(8, Math.min(width - fm.stringWidth(text) - 8, fillWidth - fm.stringWidth(text) - 6));
            int textY = (height + fm.getAscent() - fm.getDescent()) / 2;
            g2.drawString(text, textX, textY);
            g2.dispose();
        }
    }
}
