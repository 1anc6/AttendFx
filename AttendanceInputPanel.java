import java.awt.*;
import java.awt.event.*;
import java.time.LocalDate;
import javax.swing.*;
import javax.swing.table.*;

public class AttendanceInputPanel extends JPanel implements AttendanceChangeListener {

    private static final Color APP_BG             = new Color(245, 247, 251);
    private static final Color PANEL_BG           = Color.WHITE;
    private static final Color PANEL_BORDER       = new Color(219, 226, 239);
    private static final Color HEADER_BG          = new Color(232, 238, 248);
    private static final Color HEADER_FG          = new Color(34, 52, 92);
    private static final Color ROW_EVEN           = Color.WHITE;
    private static final Color ROW_ODD            = new Color(248, 250, 255);
    private static final Color ROW_HOVER          = new Color(227, 239, 255);
    private static final Color ROW_SELECTED       = new Color(205, 226, 251);
    private static final Color FIELD_BG           = new Color(249, 251, 255);
    private static final Color DELETE_RED         = new Color(220, 73, 73);
    private static final Color DELETE_RED_HOVER   = new Color(188, 44, 44);
    private static final Color PRIMARY_BLUE       = new Color(55, 115, 230);
    private static final Color PRIMARY_BLUE_DARK  = new Color(35, 85, 190);
    private static final String DELETE_LABEL      = "\uD83D\uDDD1 Delete";

    private static final String[] COLUMNS = {
        "Subject", "Total", "Attended", "%",
        "Needed", "Allowable Absences", "Status", "Action"
    };

    private DefaultTableModel model;
    private JTable            table;
    private JTextField        nameField, totalField, presentField;
    private JTextField        startDateField, endDateField;
    private int hoveredRow = -1;

    private final AttendanceService service;

    public AttendanceInputPanel() {
        service = AttendanceService.getInstance();
        service.addListener(this);

        setLayout(new BorderLayout(10, 10));
        setBackground(APP_BG);
        setBorder(BorderFactory.createEmptyBorder(10, 10, 10, 0));

        add(createSessionPanel(), BorderLayout.NORTH);
        add(createTablePanel(),   BorderLayout.CENTER);
        add(createSubjectPanel(), BorderLayout.SOUTH);
    }

    private JPanel createSessionPanel() {
        RoundedPanel card = createCardPanel();
        card.setLayout(new GridBagLayout());
        card.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createTitledBorder(
                BorderFactory.createLineBorder(PANEL_BORDER, 1, true),
                "Session Setup"
            ),
            BorderFactory.createEmptyBorder(8, 12, 10, 12)
        ));

        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(6, 8, 6, 8);
        gbc.anchor = GridBagConstraints.WEST;

        gbc.gridx = 0; gbc.gridy = 0;
        JLabel startLabel = new JLabel("Start Date (YYYY-MM-DD)");
        startLabel.setFont(new Font("Segoe UI", Font.BOLD, 13));
        card.add(startLabel, gbc);
        gbc.gridx = 1;
        gbc.fill = GridBagConstraints.HORIZONTAL;
        startDateField = createStyledField(12);
        card.add(startDateField, gbc);
        gbc.fill = GridBagConstraints.NONE;

        gbc.gridx = 0; gbc.gridy = 1;
        JLabel endLabel = new JLabel("End Date (YYYY-MM-DD)");
        endLabel.setFont(new Font("Segoe UI", Font.BOLD, 13));
        card.add(endLabel, gbc);
        gbc.gridx = 1;
        gbc.fill = GridBagConstraints.HORIZONTAL;
        endDateField = createStyledField(12);
        card.add(endDateField, gbc);
        gbc.fill = GridBagConstraints.NONE;

        gbc.gridx = 2; gbc.gridy = 0; gbc.gridheight = 2;
        gbc.anchor = GridBagConstraints.CENTER;
        JButton setBtn = new PrimaryButton("Set Session", new Color(61, 110, 203), new Color(42, 86, 170));
        setBtn.setPreferredSize(new Dimension(155, 38));
        card.add(setBtn, gbc);

        setBtn.addActionListener(e -> handleSetSession());

        return card;
    }

    private JPanel createTablePanel() {
        JPanel panel = new JPanel(new BorderLayout(0, 10));
        panel.setOpaque(false);

        model = new DefaultTableModel(COLUMNS, 0) {
            @Override public boolean isCellEditable(int r, int c) { return c == 7; }
        };

        table = new JTable(model);
        table.setFillsViewportHeight(true);
        table.setRowHeight(34);
        table.setIntercellSpacing(new Dimension(0, 0));
        table.setShowGrid(false);
        table.setSelectionBackground(ROW_SELECTED);
        table.setSelectionForeground(new Color(25, 37, 63));
        table.setBackground(PANEL_BG);
        table.setForeground(new Color(36, 48, 72));
        table.setFont(new Font("Segoe UI", Font.PLAIN, 13));
        table.setBorder(BorderFactory.createEmptyBorder());
        table.setDefaultRenderer(Object.class, new AttendanceTableRenderer());
        table.getTableHeader().setDefaultRenderer(new HeaderRenderer());
        table.getTableHeader().setPreferredSize(new Dimension(0, 38));
        table.getTableHeader().setReorderingAllowed(false);
        table.getTableHeader().setOpaque(false);
        table.setDefaultRenderer(Object.class, new StatusColorRenderer());
        table.addMouseMotionListener(new MouseMotionAdapter() {
            @Override
            public void mouseMoved(MouseEvent e) {
                int newHoverRow = table.rowAtPoint(e.getPoint());
                if (hoveredRow != newHoverRow) {
                    hoveredRow = newHoverRow;
                    table.repaint();
                }
            }
        });
        table.addMouseListener(new MouseAdapter() {
            @Override
            public void mouseExited(MouseEvent e) {
                hoveredRow = -1;
                table.repaint();
            }
        });
        table.getColumn("Action").setCellRenderer(new ButtonRenderer());
        table.getColumn("Action").setCellEditor(new SubjectDeleteEditor());
        table.getSelectionModel().addListSelectionListener(e -> {
            if (e.getValueIsAdjusting()) return;
            int row = table.getSelectedRow();
            if (row < 0) {
                service.setCalendarSubjectFilter(null);
                return;
            }
            int modelRow = table.convertRowIndexToModel(row);
            service.setCalendarSubjectFilter(String.valueOf(model.getValueAt(modelRow, 0)));
        });

        int[] widths = {170, 90, 100, 80, 100, 150, 150, 118};
        for (int i = 0; i < widths.length; i++) {
            table.getColumnModel().getColumn(i).setPreferredWidth(widths[i]);
        }

        JScrollPane scrollPane = new JScrollPane(table);
        scrollPane.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(PANEL_BORDER, 1, true),
            BorderFactory.createEmptyBorder(6, 6, 6, 6)
        ));
        scrollPane.getViewport().setBackground(PANEL_BG);

        panel.add(scrollPane, BorderLayout.CENTER);
        panel.add(createEmptyStateHint(), BorderLayout.SOUTH);
        return panel;
    }

    private JPanel createSubjectPanel() {
        RoundedPanel card = createCardPanel();
        card.setLayout(new GridBagLayout());
        card.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createTitledBorder(
                BorderFactory.createLineBorder(PANEL_BORDER, 1, true),
                "Add Subject"
            ),
            BorderFactory.createEmptyBorder(10, 14, 14, 14)
        ));

        GridBagConstraints gbc = new GridBagConstraints();
        gbc.insets = new Insets(5, 10, 5, 10);
        gbc.fill   = GridBagConstraints.HORIZONTAL;
        gbc.anchor = GridBagConstraints.WEST;

        String[] labels = {"Subject", "Total Classes", "Attended"};
        for (int i = 0; i < labels.length; i++) {
            gbc.gridx = i; gbc.gridy = 0;
            gbc.weightx = 1.0;
            JLabel label = new JLabel(labels[i]);
            label.setFont(new Font("Segoe UI", Font.BOLD, 13));
            card.add(label, gbc);
        }

        gbc.gridy = 1;
        gbc.gridx = 0; nameField    = new PlaceholderTextField("Enter subject name", 12); card.add(nameField,    gbc);
        gbc.gridx = 1; totalField   = new PlaceholderTextField("Total classes", 10);      card.add(totalField,   gbc);
        gbc.gridx = 2; presentField = new PlaceholderTextField("Classes attended", 10);   card.add(presentField, gbc);

        gbc.gridx = 3;
        gbc.weightx = 0.0;
        JButton addBtn = new PrimaryButton("Add", PRIMARY_BLUE, PRIMARY_BLUE_DARK);
        addBtn.setPreferredSize(new Dimension(104, 40));
        card.add(addBtn, gbc);
        addBtn.addActionListener(e -> handleAddSubject());

        return card;
    }

    private void handleSetSession() {
        String start = startDateField.getText().trim();
        String end   = endDateField.getText().trim();

        if (start.isEmpty() || end.isEmpty()) {
            showError("Please enter both start and end dates.");
            return;
        }

        boolean ok = service.setSession(start, end);
        if (ok) {
            JOptionPane.showMessageDialog(this, "Session set successfully!");
        } else {
            showError("Invalid dates. Use format YYYY-MM-DD and ensure end is after start.");
        }
    }

    private void handleAddSubject() {
        if (!service.isSessionSet()) {
            showError("Please set the session first.");
            return;
        }

        String error = service.addSubject(
            nameField.getText(),
            totalField.getText(),
            presentField.getText()
        );

        if (error != null) {
            showError(error);
        } else {
            clearFields();
        }
    }

    @Override
    public void onDataLoaded() {

        SwingUtilities.invokeLater(() -> {
            model.setRowCount(0);
            for (Subject s : service.getSubjects()) {
                appendSubjectRow(s);
            }

            if (service.isSessionSet()) {
                SessionInfo sess = service.getSession();
                startDateField.setText(sess.getStartDate().toString());
                endDateField.setText(sess.getEndDate().toString());
            }
        });
    }

    @Override
    public void onSessionChanged(SessionInfo session) {

    }

    @Override
    public void onSubjectAdded(Subject subject) {
        SwingUtilities.invokeLater(() -> appendSubjectRow(subject));
    }

    @Override
    public void onDailyAttendanceChanged(LocalDate date, Boolean attended) {

    }

    private void appendSubjectRow(Subject s) {
        int    needed  = service.calculateNeeded(s.totalClasses, s.attendedClasses);
        int    allowed = service.calculateAllowableAbsences(s.totalClasses, s.attendedClasses);
        double pct     = s.getPercentage();
        String status  = service.buildStatus(pct, needed);

        model.addRow(new Object[]{
            s.name, s.totalClasses, s.attendedClasses,
            String.format("%.2f", pct), needed, allowed, status, DELETE_LABEL
        });
    }

    private void clearFields() {
        nameField.setText("");
        totalField.setText("");
        presentField.setText("");
        nameField.requestFocus();
    }

    private void showError(String msg) {
        JOptionPane.showMessageDialog(this, msg, "Input Error", JOptionPane.ERROR_MESSAGE);
    }

    private void handleDeleteSubject(int row) {
        if (row < 0 || row >= model.getRowCount()) {
            showError("No subject selected.");
            return;
        }

        String subject = String.valueOf(model.getValueAt(row, 0));
        int confirm = JOptionPane.showConfirmDialog(
            this,
            "Are you sure you want to delete this subject?",
            "Confirm Delete",
            JOptionPane.YES_NO_OPTION
        );

        if (confirm != JOptionPane.YES_OPTION) return;

        String error = service.deleteSubject(subject);
        if (error != null) showError(error);
    }

    private RoundedPanel createCardPanel() {
        RoundedPanel panel = new RoundedPanel(24, PANEL_BG);
        panel.setOpaque(false);
        return panel;
    }

    private JTextField createStyledField(int columns) {
        JTextField field = new JTextField(columns);
        field.setFont(new Font("Segoe UI", Font.PLAIN, 13));
        field.setBackground(FIELD_BG);
        field.setBorder(BorderFactory.createCompoundBorder(
            BorderFactory.createLineBorder(new Color(205, 214, 230), 1, true),
            BorderFactory.createEmptyBorder(8, 10, 8, 10)
        ));
        return field;
    }

    private JPanel createEmptyStateHint() {
        RoundedPanel hint = new RoundedPanel(22, new Color(236, 244, 255));
        hint.setLayout(new BorderLayout(10, 0));
        hint.setBorder(BorderFactory.createEmptyBorder(12, 14, 12, 14));

        JLabel title = new JLabel("Keep attendance above 75%");
        title.setFont(new Font("Segoe UI", Font.BOLD, 14));
        title.setForeground(new Color(31, 73, 125));

        JLabel body = new JLabel(
            "<html>Use the calendar to mark days consistently and watch the summary cards update in real time.</html>"
        );
        body.setFont(new Font("Segoe UI", Font.PLAIN, 12));
        body.setForeground(new Color(61, 86, 122));

        hint.add(title, BorderLayout.NORTH);
        hint.add(body, BorderLayout.CENTER);
        return hint;
    }

    private class HeaderRenderer extends DefaultTableCellRenderer {
        HeaderRenderer() {
            setHorizontalAlignment(SwingConstants.CENTER);
            setOpaque(true);
        }

        @Override
        public Component getTableCellRendererComponent(
            JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int column
        ) {
            super.getTableCellRendererComponent(table, value, false, false, row, column);
            setFont(new Font("Segoe UI", Font.BOLD, 13));
            setBackground(HEADER_BG);
            setForeground(HEADER_FG);
            setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createMatteBorder(0, 0, 1, 1, new Color(214, 223, 238)),
                BorderFactory.createEmptyBorder(8, 10, 8, 10)
            ));
            return this;
        }
    }

    private class AttendanceTableRenderer extends DefaultTableCellRenderer {
        @Override
        public Component getTableCellRendererComponent(
            JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int column
        ) {
            super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column);
            setBorder(BorderFactory.createEmptyBorder(8, 10, 8, 10));
            setFont(new Font("Segoe UI", Font.PLAIN, 13));
            setForeground(new Color(31, 42, 67));
            setHorizontalAlignment(column == 0 || column == 6 ? SwingConstants.LEFT : SwingConstants.CENTER);
            if (isSelected) {
                setBackground(ROW_SELECTED);
            } else if (row == hoveredRow) {
                setBackground(ROW_HOVER);
            } else {
                setBackground(row % 2 == 0 ? ROW_EVEN : ROW_ODD);
            }
            return this;
        }
    }

    private class StatusColorRenderer extends AttendanceTableRenderer {
        @Override
        public Component getTableCellRendererComponent(
            JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int column
        ) {
            if (column == 6) {
                StatusBadge badge = new StatusBadge(String.valueOf(value));
                badge.setSelected(isSelected || row == hoveredRow);
                return badge;
            }
            return super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column);
        }
    }

    private static class ButtonRenderer implements TableCellRenderer {
        private final JButton button = createDeleteButton();

        @Override
        public Component getTableCellRendererComponent(
            JTable table, Object value, boolean isSelected, boolean hasFocus, int row, int column
        ) {
            button.setText(String.valueOf(value));
            button.setBackground(isSelected ? DELETE_RED_HOVER : DELETE_RED);
            return button;
        }
    }

    private class SubjectDeleteEditor extends DefaultCellEditor {
        private final JButton button = createDeleteButton();
        private int row = -1;

        SubjectDeleteEditor() {
            super(new JCheckBox());
            button.addActionListener(e -> {
                fireEditingStopped();
                handleDeleteSubject(row);
            });
        }

        @Override
        public Component getTableCellEditorComponent(
            JTable table, Object value, boolean isSelected, int row, int column
        ) {
            this.row = table.convertRowIndexToModel(row);
            button.setText(String.valueOf(value));
            button.setBackground(DELETE_RED_HOVER);
            return button;
        }

        @Override
        public Object getCellEditorValue() {
            return DELETE_LABEL;
        }
    }

    private static JButton createDeleteButton() {
        JButton button = new JButton(DELETE_LABEL);
        button.setForeground(Color.WHITE);
        button.setBackground(DELETE_RED);
        button.setFocusPainted(false);
        button.setBorder(BorderFactory.createEmptyBorder(8, 12, 8, 12));
        button.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        button.setFont(new Font("Segoe UI", Font.BOLD, 12));
        button.setOpaque(true);
        return button;
    }

    private static class StatusBadge extends JPanel {
        private final PillLabel label;

        StatusBadge(String rawStatus) {
            setOpaque(false);
            setLayout(new FlowLayout(FlowLayout.LEFT, 0, 4));
            label = new PillLabel();
            add(label);
            setStatus(rawStatus);
        }

        void setSelected(boolean selected) {
            setBackground(selected ? ROW_HOVER : null);
        }

        private void setStatus(String rawStatus) {
            String normalized = rawStatus == null ? "" : rawStatus.toUpperCase();
            Color badgeColor = new Color(89, 169, 98);
            String text = "SAFE";
            if (normalized.contains("CRITICAL")) {
                badgeColor = new Color(222, 84, 84);
                text = "CRITICAL";
            } else if (normalized.contains("WARNING") || normalized.contains("POSSIBLE")) {
                badgeColor = new Color(226, 182, 63);
                text = normalized.contains("WARNING") ? "WARNING" : "POSSIBLE";
            }
            label.setColors(badgeColor, Color.WHITE);
            label.setText(text);
        }
    }

    private static class PillLabel extends JLabel {
        private Color bg = Color.GRAY;
        private Color fg = Color.WHITE;

        PillLabel() {
            setOpaque(false);
            setFont(new Font("Segoe UI", Font.BOLD, 12));
            setBorder(BorderFactory.createEmptyBorder(4, 12, 4, 12));
        }

        void setColors(Color background, Color foreground) {
            this.bg = background;
            this.fg = foreground;
            setForeground(foreground);
        }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g2.setColor(bg);
            g2.fillRoundRect(0, 0, getWidth(), getHeight(), getHeight(), getHeight());
            g2.dispose();
            super.paintComponent(g);
        }
    }

    private static class PlaceholderTextField extends JTextField {
        private final String placeholder;

        PlaceholderTextField(String placeholder, int columns) {
            super(columns);
            this.placeholder = placeholder;
            setFont(new Font("Segoe UI", Font.PLAIN, 13));
            setBackground(FIELD_BG);
            setBorder(BorderFactory.createCompoundBorder(
                BorderFactory.createLineBorder(new Color(205, 214, 230), 1, true),
                BorderFactory.createEmptyBorder(8, 10, 8, 10)
            ));
        }

        @Override
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);
            if (!getText().isEmpty() || isFocusOwner()) return;

            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_TEXT_ANTIALIASING, RenderingHints.VALUE_TEXT_ANTIALIAS_ON);
            g2.setColor(new Color(154, 164, 184));
            g2.setFont(getFont());
            Insets insets = getInsets();
            FontMetrics fm = g2.getFontMetrics();
            g2.drawString(placeholder, insets.left, (getHeight() + fm.getAscent() - fm.getDescent()) / 2);
            g2.dispose();
        }
    }

    private static class PrimaryButton extends JButton {
        private final Color startColor;
        private final Color endColor;
        private boolean hovered;

        PrimaryButton(String text, Color startColor, Color endColor) {
            super(text);
            this.startColor = startColor;
            this.endColor = endColor;
            setContentAreaFilled(false);
            setFocusPainted(false);
            setForeground(Color.WHITE);
            setFont(new Font("Segoe UI", Font.BOLD, 14));
            setBorder(BorderFactory.createEmptyBorder(10, 18, 10, 18));
            setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
            addMouseListener(new MouseAdapter() {
                @Override public void mouseEntered(MouseEvent e) { hovered = true; repaint(); }
                @Override public void mouseExited(MouseEvent e)  { hovered = false; repaint(); }
            });
        }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            Color top = hovered ? endColor : startColor;
            Color bottom = hovered ? endColor.darker() : endColor;
            g2.setPaint(new GradientPaint(0, 0, top, 0, getHeight(), bottom));
            g2.fillRoundRect(0, 0, getWidth(), getHeight(), 18, 18);
            if (hovered) {
                g2.translate(0, -1);
            }
            g2.dispose();
            super.paintComponent(g);
        }
    }
}
