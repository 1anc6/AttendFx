import java.awt.*;
import java.io.File;
import java.time.LocalDate;
import javax.swing.*;
import javax.swing.table.DefaultTableModel;
import javax.swing.table.DefaultTableCellRenderer;
import javax.swing.table.TableCellRenderer;
import javax.swing.table.TableCellEditor;
import javax.swing.table.TableRowSorter;

public class TeacherDashboard extends JFrame implements AttendanceChangeListener {

    private static final Color BG = new Color(245, 245, 245);
    private static final Color SIDEBAR = new Color(15, 35, 120);
    private static final Color ACCENT = new Color(115, 120, 255);

    private final AttendanceService service = AttendanceService.getInstance();

    private JLabel totalStudentsLabel;
    private JLabel totalClassesLabel;
    private JLabel classesTillNowLabel;
    private JLabel averageAttendanceLabel;

    private DefaultTableModel tableModel;
    private JTable studentTable;
    private TableRowSorter<DefaultTableModel> sorter;
    private JTextField searchField;
    private JComboBox<String> attendanceFilter;
    private JTextField courseFilter;
    private JTextField sectionFilter;
    private DefaultTableModel subjectTableModel;
    private JTable subjectTable;
    private JPanel classesTillNowCard;
    private CardLayout cardLayout;
    private JPanel contentPanel;
    private DefaultTableModel studentsManagerModel;
    private DefaultTableModel attendanceManagerModel;
    private JComboBox<String> attendanceCourseSelector;
    private JComboBox<String> attendanceSectionSelector;

    public TeacherDashboard(String username) {
        setTitle("Teacher Dashboard");
        setSize(1200, 720);
        setLocationRelativeTo(null);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);
        setLayout(new BorderLayout());

        service.addListener(this);

        add(createSidebar(), BorderLayout.WEST);
        add(createContent(), BorderLayout.CENTER);

        setVisible(true);
        SwingUtilities.invokeLater(service::notifyDataLoaded);
    }

    private JPanel createSidebar() {
        JPanel sidebar = new JPanel();
        sidebar.setPreferredSize(new Dimension(220, 720));
        sidebar.setBackground(SIDEBAR);
        sidebar.setLayout(new BoxLayout(sidebar, BoxLayout.Y_AXIS));
        sidebar.setBorder(BorderFactory.createEmptyBorder(20, 10, 20, 10));

        JLabel title = new JLabel("Teacher");
        title.setForeground(Color.WHITE);
        title.setFont(new Font("Segoe UI", Font.BOLD, 22));
        title.setAlignmentX(Component.CENTER_ALIGNMENT);

        sidebar.add(title);
        sidebar.add(Box.createVerticalStrut(25));
        JButton dashboardButton = sideButton("Dashboard");
        JButton studentsButton = sideButton("Students");
        JButton attendanceButton = sideButton("Attendance");
        dashboardButton.addActionListener(e -> showView("DASHBOARD"));
        studentsButton.addActionListener(e -> showView("STUDENTS"));
        attendanceButton.addActionListener(e -> showView("ATTENDANCE"));
        sidebar.add(dashboardButton);
        sidebar.add(studentsButton);
        sidebar.add(attendanceButton);
        sidebar.add(Box.createVerticalGlue());

        JButton logout = sideButton("Logout");
        logout.addActionListener(e -> {
            try {
                new ModernLoginUI();
                dispose();
            } catch (Exception ex) {
                showError("Logout error: " + ex.getMessage());
            }
        });
        sidebar.add(logout);

        return sidebar;
    }

    private JButton sideButton(String text) {
        JButton btn = new JButton(text);
        btn.setMaximumSize(new Dimension(190, 40));
        btn.setAlignmentX(Component.CENTER_ALIGNMENT);
        btn.setForeground(Color.WHITE);
        btn.setBackground(SIDEBAR);
        btn.setFocusPainted(false);
        return btn;
    }

    private JPanel createContent() {
        cardLayout = new CardLayout();
        contentPanel = new JPanel(cardLayout);
        contentPanel.setBackground(BG);
        contentPanel.add(createDashboardView(), "DASHBOARD");
        contentPanel.add(createStudentsView(), "STUDENTS");
        contentPanel.add(createAttendanceView(), "ATTENDANCE");
        return contentPanel;
    }

    private JPanel createDashboardView() {
        JPanel content = new JPanel(new BorderLayout(20, 20));
        content.setBackground(BG);
        content.setBorder(BorderFactory.createEmptyBorder(25, 25, 25, 25));

        JPanel top = new JPanel(new BorderLayout());
        top.setOpaque(false);
        JLabel heading = new JLabel("Teachers");
        heading.setFont(new Font("Segoe UI", Font.BOLD, 32));
        top.add(heading, BorderLayout.WEST);
        content.add(top, BorderLayout.NORTH);

        JPanel body = new JPanel(new BorderLayout(20, 20));
        body.setOpaque(false);
        body.add(createCards(), BorderLayout.NORTH);
        body.add(createTable(), BorderLayout.CENTER);
        body.add(createSubjectDetailTable(), BorderLayout.SOUTH);
        content.add(body, BorderLayout.CENTER);

        return content;
    }

    private JPanel viewPanel(String headingText) {
        JPanel content = new JPanel(new BorderLayout(20, 20));
        content.setBackground(BG);
        content.setBorder(BorderFactory.createEmptyBorder(25, 25, 25, 25));

        JLabel heading = new JLabel(headingText);
        heading.setFont(new Font("Segoe UI", Font.BOLD, 32));
        JPanel top = new JPanel(new BorderLayout());
        top.setOpaque(false);
        top.add(heading, BorderLayout.WEST);
        content.add(top, BorderLayout.NORTH);
        return content;
    }

    private void showView(String name) {
        if ("DASHBOARD".equals(name)) refreshDashboard();
        if ("STUDENTS".equals(name)) refreshStudentsManagerRows();
        if ("ATTENDANCE".equals(name)) {
            refreshAttendanceSelectors();
            refreshAttendanceRows();
        }
        cardLayout.show(contentPanel, name);
    }

    private JPanel createCards() {
        JPanel cards = new JPanel(new GridLayout(1, 4, 18, 18));
        cards.setOpaque(false);

        totalStudentsLabel = metricValue("0");
        totalClassesLabel = metricValue("0");
        classesTillNowLabel = metricValue("0");
        averageAttendanceLabel = metricValue("0%");

        cards.add(metricCard("Total Students", totalStudentsLabel, "Fetched from shared data"));
        cards.add(metricCard("Total Classes", totalClassesLabel, "Working days in session"));
        classesTillNowCard = metricCard("Total Classes Till Now", classesTillNowLabel, "Click to update");
        classesTillNowCard.setCursor(Cursor.getPredefinedCursor(Cursor.HAND_CURSOR));
        classesTillNowCard.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override public void mouseClicked(java.awt.event.MouseEvent e) { updateClassesTillNow(); }
        });
        cards.add(classesTillNowCard);
        cards.add(metricCard("Average Attendance", averageAttendanceLabel, "All students"));
        return cards;
    }

    private JLabel metricValue(String value) {
        JLabel label = new JLabel(value);
        label.setFont(new Font("Segoe UI", Font.BOLD, 34));
        label.setForeground(new Color(20, 20, 20));
        return label;
    }

    private JPanel metricCard(String title, JLabel value, String footer) {
        RoundedPanel card = new RoundedPanel(20, Color.WHITE);
        card.setLayout(new BorderLayout(8, 8));
        card.setBorder(BorderFactory.createEmptyBorder(18, 20, 18, 20));

        JLabel titleLabel = new JLabel(title.toUpperCase());
        titleLabel.setFont(new Font("Segoe UI", Font.PLAIN, 12));
        titleLabel.setForeground(new Color(80, 80, 90));

        JLabel footerLabel = new JLabel(footer);
        footerLabel.setFont(new Font("Segoe UI", Font.PLAIN, 12));
        footerLabel.setForeground(new Color(95, 95, 105));

        card.add(titleLabel, BorderLayout.NORTH);
        card.add(value, BorderLayout.CENTER);
        card.add(footerLabel, BorderLayout.SOUTH);
        return wrapShadow(card);
    }

    private JPanel createTable() {
        String[] columns = {
            "University Roll No", "Class Roll No", "Student Name",
            "Total Classes", "Classes Attended", "Attendance %", "Status", "Course", "Section", "Action"
        };
        tableModel = new DefaultTableModel(columns, 0) {
            @Override public boolean isCellEditable(int row, int col) { return col == 9; }
        };

        studentTable = new JTable(tableModel);
        studentTable.setRowHeight(34);
        studentTable.setFillsViewportHeight(true);
        studentTable.getTableHeader().setFont(new Font("Segoe UI", Font.BOLD, 12));
        studentTable.setSelectionBackground(new Color(180, 205, 230));
        studentTable.setDefaultRenderer(Object.class, new StatusColorRenderer());
        sorter = new TableRowSorter<>(tableModel);
        studentTable.setRowSorter(sorter);
        studentTable.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        studentTable.getColumn("Action").setCellRenderer(new DeleteButtonRenderer());
        studentTable.getColumn("Action").setCellEditor(new DeleteButtonEditor());
        studentTable.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override public void mouseClicked(java.awt.event.MouseEvent e) {
                if (e.getClickCount() == 2 && studentTable.getSelectedRow() >= 0) showSelectedStudentDetails();
            }
        });
        studentTable.getSelectionModel().addListSelectionListener(e -> {
            if (!e.getValueIsAdjusting()) updateSelectedStudentDetail();
        });

        JScrollPane scroll = new JScrollPane(studentTable);
        scroll.setBorder(BorderFactory.createEmptyBorder());

        RoundedPanel tableCard = new RoundedPanel(20, Color.WHITE);
        tableCard.setLayout(new BorderLayout());
        tableCard.setBorder(BorderFactory.createEmptyBorder(8, 8, 8, 8));
        tableCard.add(createFilterBar(), BorderLayout.NORTH);
        tableCard.add(scroll, BorderLayout.CENTER);
        return wrapShadow(tableCard);
    }

    private JPanel createFilterBar() {
        JPanel bar = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 4));
        bar.setOpaque(false);

        searchField = new JTextField(14);
        attendanceFilter = new JComboBox<>(new String[] {"All", "Low Attendance"});
        courseFilter = new JTextField(10);
        sectionFilter = new JTextField(8);
        JButton apply = actionButton("Filter");
        JButton clear = actionButton("Clear");
        JButton export = actionButton("Export CSV");

        apply.addActionListener(e -> applyFilters());
        clear.addActionListener(e -> {
            searchField.setText("");
            courseFilter.setText("");
            sectionFilter.setText("");
            attendanceFilter.setSelectedIndex(0);
            applyFilters();
        });
        export.addActionListener(e -> exportCsv());

        bar.add(new JLabel("Search"));
        bar.add(searchField);
        bar.add(new JLabel("Attendance"));
        bar.add(attendanceFilter);
        bar.add(new JLabel("Course"));
        bar.add(courseFilter);
        bar.add(new JLabel("Section"));
        bar.add(sectionFilter);
        bar.add(apply);
        bar.add(clear);
        bar.add(export);
        return bar;
    }

    private JPanel createSubjectDetailTable() {
        String[] columns = {"Subject Name", "Total Classes", "Classes Attended", "Attendance %", "Status"};
        subjectTableModel = new DefaultTableModel(columns, 0) {
            @Override public boolean isCellEditable(int row, int col) { return false; }
        };

        subjectTable = new JTable(subjectTableModel);
        subjectTable.setRowHeight(30);
        subjectTable.setFillsViewportHeight(true);
        subjectTable.getTableHeader().setFont(new Font("Segoe UI", Font.BOLD, 12));

        JScrollPane scroll = new JScrollPane(subjectTable);
        scroll.setBorder(BorderFactory.createEmptyBorder());
        scroll.setPreferredSize(new Dimension(1000, 170));

        RoundedPanel tableCard = new RoundedPanel(20, Color.WHITE);
        tableCard.setLayout(new BorderLayout());
        tableCard.setBorder(BorderFactory.createTitledBorder("Subject-wise Details"));
        tableCard.add(scroll, BorderLayout.CENTER);
        return wrapShadow(tableCard);
    }

    private JPanel wrapShadow(JPanel panel) {
        ShadowPanel shadow = new ShadowPanel(new BorderLayout());
        shadow.add(panel, BorderLayout.CENTER);
        return shadow;
    }

    private JButton actionButton(String text) {
        JButton button = new JButton(text);
        button.setForeground(Color.WHITE);
        button.setBackground(ACCENT);
        button.setFocusPainted(false);
        button.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override public void mouseEntered(java.awt.event.MouseEvent e) { button.setBackground(new Color(90, 95, 240)); }
            @Override public void mouseExited(java.awt.event.MouseEvent e) { button.setBackground(ACCENT); }
        });
        return button;
    }

    private void refreshDashboard() {
        String selectedRoll = getSelectedUniversityRoll();
        tableModel.setRowCount(0);

        for (StudentRecord student : service.getStudents()) {
            int[] totals = service.getSubjectTotalsForStudent(student.universityRollNo);
            int totalClasses = totals[0];
            int attendedClasses = totals[1];
            double pct = totalClasses == 0 ? 0.0 : (attendedClasses * 100.0) / totalClasses;
            tableModel.addRow(new Object[] {
                safe(student.universityRollNo),
                safe(student.classRollNo),
                student.name,
                totalClasses,
                attendedClasses,
                String.format("%.2f%%", pct),
                service.getStatusLabel(pct),
                safe(student.course),
                safe(student.section),
                "Delete"
            });
        }

        totalStudentsLabel.setText(String.valueOf(service.getTotalStudents()));
        totalClassesLabel.setText(String.valueOf(service.getTotalWorkingDaysInSession()));
        classesTillNowLabel.setText(String.valueOf(service.getClassesTillToday()));
        averageAttendanceLabel.setText(String.format("%.2f%%", service.getAverageStudentAttendance()));

        restoreSelection(selectedRoll);
        updateSelectedStudentDetail();
    }

    private void updateSelectedStudentDetail() {
        int row = studentTable.getSelectedRow();
        if (row < 0) {
            renderSubjectRows(null);
            return;
        }

        int modelRow = studentTable.convertRowIndexToModel(row);
        String universityRoll = String.valueOf(tableModel.getValueAt(modelRow, 0));
        StudentRecord student = findDisplayedStudent(universityRoll);
        if (student == null) {
            renderSubjectRows(null);
            return;
        }

        renderSubjectRows(student);
    }

    private void renderSubjectRows(StudentRecord student) {
        subjectTableModel.setRowCount(0);
        if (student == null) {
            subjectTableModel.addRow(new Object[] {"No subject data available", "", "", "", ""});
            return;
        }

        java.util.List<Subject> subjects = service.getSubjectsForStudent(student.universityRollNo);
        if (subjects.isEmpty()) {
            subjectTableModel.addRow(new Object[] {"No subject data available", "", "", "", ""});
            return;
        }

        for (Subject subject : subjects) {
            double pct = subject.getPercentage();
            subjectTableModel.addRow(new Object[] {
                safe(subject.name),
                subject.totalClasses,
                subject.attendedClasses,
                String.format("%.2f%%", pct),
                service.getStatusLabel(pct)
            });
        }
    }

    private void applyFilters() {
        java.util.List<RowFilter<Object, Object>> filters = new java.util.ArrayList<>();
        String search = searchField.getText().trim();
        String course = courseFilter.getText().trim();
        String section = sectionFilter.getText().trim();

        if (!search.isEmpty()) filters.add(RowFilter.regexFilter("(?i)" + java.util.regex.Pattern.quote(search), 0, 1, 2));
        if (!course.isEmpty()) filters.add(RowFilter.regexFilter("(?i)" + java.util.regex.Pattern.quote(course), 7));
        if (!section.isEmpty()) filters.add(RowFilter.regexFilter("(?i)" + java.util.regex.Pattern.quote(section), 8));
        if ("Low Attendance".equals(attendanceFilter.getSelectedItem())) {
            filters.add(new RowFilter<Object, Object>() {
                @Override public boolean include(Entry<?, ?> entry) {
                    String value = String.valueOf(entry.getValue(5)).replace("%", "");
                    try { return Double.parseDouble(value) < AttendanceService.REQUIRED_PCT; }
                    catch (NumberFormatException e) { return false; }
                }
            });
        }

        sorter.setRowFilter(filters.isEmpty() ? null : RowFilter.andFilter(filters));
    }

    private void exportCsv() {
        JFileChooser chooser = new JFileChooser();
        chooser.setSelectedFile(new File("attendance_export.csv"));
        if (chooser.showSaveDialog(this) != JFileChooser.APPROVE_OPTION) return;

        String error = service.exportAttendanceCsv(chooser.getSelectedFile());
        if (error != null) showError(error);
        else JOptionPane.showMessageDialog(this, "Attendance data exported successfully.");
    }

    private JPanel createStudentsView() {
        JPanel content = viewPanel("Students");
        studentsManagerModel = new DefaultTableModel(
            new String[] {"University Roll No", "Class Roll No", "Student Name", "Course", "Section"}, 0
        ) {
            @Override public boolean isCellEditable(int row, int col) { return false; }
        };
        JTable table = new JTable(studentsManagerModel);
        table.setSelectionMode(ListSelectionModel.SINGLE_SELECTION);
        table.setRowHeight(30);
        TableRowSorter<DefaultTableModel> dialogSorter = new TableRowSorter<>(studentsManagerModel);
        table.setRowSorter(dialogSorter);

        JTextField search = new JTextField(18);
        JButton add = actionButton("Add Student");
        JButton edit = actionButton("Edit Student");
        JButton delete = actionButton("Delete Student");
        JPanel top = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 8));
        top.add(new JLabel("Search"));
        top.add(search);
        top.add(add);
        top.add(edit);
        top.add(delete);

        search.getDocument().addDocumentListener(new javax.swing.event.DocumentListener() {
            public void insertUpdate(javax.swing.event.DocumentEvent e) { filter(); }
            public void removeUpdate(javax.swing.event.DocumentEvent e) { filter(); }
            public void changedUpdate(javax.swing.event.DocumentEvent e) { filter(); }
            private void filter() {
                String text = search.getText().trim();
                dialogSorter.setRowFilter(text.isEmpty()
                    ? null
                    : RowFilter.regexFilter("(?i)" + java.util.regex.Pattern.quote(text), 0, 1, 2, 3, 4));
            }
        });

        add.addActionListener(e -> {
            if (showStudentEditor(null)) {
                refreshDashboard();
                refreshStudentsManagerRows();
            }
        });
        edit.addActionListener(e -> {
            StudentRecord student = selectedStudentFrom(table, studentsManagerModel);
            if (student == null) {
                showError("Please select a student to edit.");
                return;
            }
            if (showStudentEditor(student)) {
                refreshDashboard();
                refreshStudentsManagerRows();
            }
        });
        delete.addActionListener(e -> {
            StudentRecord student = selectedStudentFrom(table, studentsManagerModel);
            if (student == null) {
                showError("Please select a student to delete.");
                return;
            }
            deleteStudentWithConfirm(student.universityRollNo);
            refreshStudentsManagerRows();
        });
        table.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override public void mouseClicked(java.awt.event.MouseEvent e) {
                if (e.getClickCount() == 2) {
                    StudentRecord student = selectedStudentFrom(table, studentsManagerModel);
                    if (student != null) showStudentDetails(student);
                }
            }
        });

        RoundedPanel card = new RoundedPanel(20, Color.WHITE);
        card.setLayout(new BorderLayout(8, 8));
        card.setBorder(BorderFactory.createEmptyBorder(8, 8, 8, 8));
        card.add(top, BorderLayout.NORTH);
        card.add(new JScrollPane(table), BorderLayout.CENTER);
        content.add(wrapShadow(card), BorderLayout.CENTER);
        refreshStudentsManagerRows();
        return content;
    }

    private JPanel createAttendanceView() {
        JPanel content = viewPanel("Attendance");
        attendanceCourseSelector = new JComboBox<>(distinctValues(true));
        attendanceSectionSelector = new JComboBox<>(distinctValues(false));
        JTextField date = new JTextField(LocalDate.now().toString(), 10);
        JButton load = actionButton("Load");
        JButton save = actionButton("Save Attendance");
        JPanel top = new JPanel(new FlowLayout(FlowLayout.LEFT, 8, 8));
        top.add(new JLabel("Course"));
        top.add(attendanceCourseSelector);
        top.add(new JLabel("Section"));
        top.add(attendanceSectionSelector);
        top.add(new JLabel("Date"));
        top.add(date);
        top.add(load);
        top.add(save);

        attendanceManagerModel = new DefaultTableModel(new String[] {
            "University Roll No", "Student Name", "Course", "Section", "Present"
        }, 0) {
            @Override public Class<?> getColumnClass(int columnIndex) {
                return columnIndex == 4 ? Boolean.class : String.class;
            }
            @Override public boolean isCellEditable(int row, int col) { return col == 4; }
        };
        JTable table = new JTable(attendanceManagerModel);
        table.setRowHeight(30);

        load.addActionListener(e -> refreshAttendanceRows());
        save.addActionListener(e -> {
            LocalDate attendanceDate;
            try {
                attendanceDate = LocalDate.parse(date.getText().trim());
            } catch (Exception ex) {
                showError("Use date format YYYY-MM-DD.");
                return;
            }
            for (int i = 0; i < attendanceManagerModel.getRowCount(); i++) {
                String roll = String.valueOf(attendanceManagerModel.getValueAt(i, 0));
                boolean present = Boolean.TRUE.equals(attendanceManagerModel.getValueAt(i, 4));
                String error = service.recordStudentAttendance(roll, attendanceDate, present);
                if (error != null) {
                    showError(error);
                    return;
                }
            }
            refreshDashboard();
            JOptionPane.showMessageDialog(this, "Attendance saved.");
        });

        RoundedPanel card = new RoundedPanel(20, Color.WHITE);
        card.setLayout(new BorderLayout(8, 8));
        card.setBorder(BorderFactory.createEmptyBorder(8, 8, 8, 8));
        card.add(top, BorderLayout.NORTH);
        card.add(new JScrollPane(table), BorderLayout.CENTER);
        content.add(wrapShadow(card), BorderLayout.CENTER);
        refreshAttendanceRows();
        return content;
    }

    private void refreshStudentsManagerRows() {
        if (studentsManagerModel == null) return;
        studentsManagerModel.setRowCount(0);
        for (StudentRecord student : service.getStudents()) {
            studentsManagerModel.addRow(new Object[] {
                safe(student.universityRollNo), safe(student.classRollNo), safe(student.name),
                safe(student.course), safe(student.section)
            });
        }
    }

    private void refreshAttendanceSelectors() {
        if (attendanceCourseSelector == null || attendanceSectionSelector == null) return;
        Object selectedCourse = attendanceCourseSelector.getSelectedItem();
        Object selectedSection = attendanceSectionSelector.getSelectedItem();
        attendanceCourseSelector.setModel(new DefaultComboBoxModel<>(distinctValues(true)));
        attendanceSectionSelector.setModel(new DefaultComboBoxModel<>(distinctValues(false)));
        if (selectedCourse != null) attendanceCourseSelector.setSelectedItem(selectedCourse);
        if (selectedSection != null) attendanceSectionSelector.setSelectedItem(selectedSection);
    }

    private void refreshAttendanceRows() {
        if (attendanceManagerModel == null) return;
        attendanceManagerModel.setRowCount(0);
        String selectedCourse = String.valueOf(attendanceCourseSelector.getSelectedItem());
        String selectedSection = String.valueOf(attendanceSectionSelector.getSelectedItem());
        for (StudentRecord student : service.getStudents()) {
            boolean courseMatch = "All".equals(selectedCourse) || safe(student.course).equalsIgnoreCase(selectedCourse);
            boolean sectionMatch = "All".equals(selectedSection) || safe(student.section).equalsIgnoreCase(selectedSection);
            if (courseMatch && sectionMatch) {
                attendanceManagerModel.addRow(new Object[] {
                    safe(student.universityRollNo), safe(student.name), safe(student.course), safe(student.section), Boolean.TRUE
                });
            }
        }
    }

    private boolean showStudentEditor(StudentRecord student) {
        JTextField name = new JTextField(student == null ? "" : safe(student.name), 18);
        JTextField universityRoll = new JTextField(student == null ? "" : safe(student.universityRollNo), 18);
        JTextField classRoll = new JTextField(student == null ? "" : safe(student.classRollNo), 18);
        JTextField course = new JTextField(student == null ? "" : safe(student.course), 18);
        JTextField section = new JTextField(student == null ? "" : safe(student.section), 18);
        JPanel form = new JPanel(new GridLayout(0, 2, 8, 8));
        form.add(new JLabel("Student Name"));
        form.add(name);
        form.add(new JLabel("University Roll No"));
        form.add(universityRoll);
        form.add(new JLabel("Class Roll No"));
        form.add(classRoll);
        form.add(new JLabel("Course"));
        form.add(course);
        form.add(new JLabel("Section"));
        form.add(section);

        int result = JOptionPane.showConfirmDialog(this, form,
            student == null ? "Add Student" : "Edit Student", JOptionPane.OK_CANCEL_OPTION);
        if (result != JOptionPane.OK_OPTION) return false;

        String error = student == null
            ? service.addStudentProfile(name.getText(), universityRoll.getText(), classRoll.getText(), section.getText(), course.getText())
            : service.updateStudentProfileByUniversityRoll(student.universityRollNo, name.getText(), universityRoll.getText(),
                classRoll.getText(), section.getText(), course.getText());
        if (error != null) {
            showError(error);
            return false;
        }
        return true;
    }

    private void updateClassesTillNow() {
        String current = service.getStoredClassesConductedTillNow() >= 0
            ? String.valueOf(service.getStoredClassesConductedTillNow())
            : String.valueOf(service.getClassesTillToday());
        String value = JOptionPane.showInputDialog(this, "Total classes conducted till now:", current);
        if (value == null) return;
        String error = service.setClassesConductedTillNow(value);
        if (error != null) showError(error);
    }

    private void showSelectedStudentDetails() {
        StudentRecord student = findDisplayedStudent(getSelectedUniversityRoll());
        if (student != null) showStudentDetails(student);
    }

    private void showStudentDetails(StudentRecord student) {
        int[] totals = service.getSubjectTotalsForStudent(student.universityRollNo);
        double pct = totals[0] == 0 ? 0.0 : (totals[1] * 100.0) / totals[0];
        JOptionPane.showMessageDialog(this,
            "Name: " + safe(student.name)
                + "\nUniversity Roll No: " + safe(student.universityRollNo)
                + "\nClass Roll No: " + safe(student.classRollNo)
                + "\nCourse: " + safe(student.course)
                + "\nSection: " + safe(student.section)
                + "\nTotal Classes: " + totals[0]
                + "\nClasses Attended: " + totals[1]
                + "\nAttendance: " + String.format("%.2f%%", pct),
            "Student Details",
            JOptionPane.INFORMATION_MESSAGE);
    }

    private StudentRecord selectedStudentFrom(JTable table, DefaultTableModel model) {
        int row = table.getSelectedRow();
        if (row < 0) return null;
        int modelRow = table.convertRowIndexToModel(row);
        return findDisplayedStudent(String.valueOf(model.getValueAt(modelRow, 0)));
    }

    private String[] distinctValues(boolean courseValues) {
        java.util.LinkedHashSet<String> values = new java.util.LinkedHashSet<>();
        values.add("All");
        for (StudentRecord student : service.getStudents()) {
            String value = courseValues ? safe(student.course) : safe(student.section);
            if (!"-".equals(value)) values.add(value);
        }
        return values.toArray(new String[0]);
    }

    private void deleteStudentWithConfirm(String universityRoll) {
        if (universityRoll == null || universityRoll.trim().isEmpty()) return;
        int confirm = JOptionPane.showConfirmDialog(this,
            "Are you sure you want to delete this student?",
            "Delete Student",
            JOptionPane.YES_NO_OPTION);
        if (confirm != JOptionPane.YES_OPTION) return;
        String error = service.deleteStudent(universityRoll);
        if (error != null) showError(error);
        else refreshDashboard();
    }

    private StudentRecord findDisplayedStudent(String universityRoll) {
        for (StudentRecord student : service.getStudents()) {
            if (safe(student.universityRollNo).equalsIgnoreCase(universityRoll)) return student;
        }
        return null;
    }

    private String getSelectedUniversityRoll() {
        if (studentTable == null || studentTable.getSelectedRow() < 0) return null;
        int row = studentTable.convertRowIndexToModel(studentTable.getSelectedRow());
        return String.valueOf(tableModel.getValueAt(row, 0));
    }

    private void restoreSelection(String universityRoll) {
        if (tableModel.getRowCount() == 0) {
            updateSelectedStudentDetail();
            return;
        }
        int rowToSelect = 0;
        if (universityRoll != null) {
            for (int i = 0; i < tableModel.getRowCount(); i++) {
                if (universityRoll.equalsIgnoreCase(String.valueOf(tableModel.getValueAt(i, 0)))) {
                    rowToSelect = i;
                    break;
                }
            }
        }
        studentTable.setRowSelectionInterval(rowToSelect, rowToSelect);
    }

    private String safe(String value) {
        return value == null || value.trim().isEmpty() ? "-" : value.trim();
    }

    private static class StatusColorRenderer extends DefaultTableCellRenderer {
        @Override
        public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected,
                                                       boolean hasFocus, int row, int column) {
            Component c = super.getTableCellRendererComponent(table, value, isSelected, hasFocus, row, column);
            if (isSelected) return c;

            String status = String.valueOf(table.getValueAt(row, 6));
            if ("SAFE".equals(status)) c.setBackground(new Color(220, 245, 220));
            else if ("WARNING".equals(status)) c.setBackground(new Color(255, 245, 190));
            else if ("CRITICAL".equals(status)) c.setBackground(new Color(255, 220, 220));
            else c.setBackground(Color.WHITE);
            return c;
        }
    }

    private class DeleteButtonRenderer extends JButton implements TableCellRenderer {
        DeleteButtonRenderer() {
            setText("Delete");
            setForeground(Color.WHITE);
            setBackground(new Color(220, 73, 73));
            setFocusPainted(false);
        }

        @Override
        public Component getTableCellRendererComponent(JTable table, Object value, boolean isSelected,
                                                       boolean hasFocus, int row, int column) {
            return this;
        }
    }

    private class DeleteButtonEditor extends AbstractCellEditor implements TableCellEditor {
        private final JButton button = new JButton("Delete");
        private String universityRoll;

        DeleteButtonEditor() {
            button.setForeground(Color.WHITE);
            button.setBackground(new Color(220, 73, 73));
            button.setFocusPainted(false);
            button.addActionListener(e -> {
                fireEditingStopped();
                deleteStudentWithConfirm(universityRoll);
            });
        }

        @Override
        public Component getTableCellEditorComponent(JTable table, Object value, boolean isSelected,
                                                     int row, int column) {
            int modelRow = table.convertRowIndexToModel(row);
            universityRoll = String.valueOf(tableModel.getValueAt(modelRow, 0));
            return button;
        }

        @Override
        public Object getCellEditorValue() {
            return "Delete";
        }
    }

    private void showError(String message) {
        JOptionPane.showMessageDialog(this, message, "Teacher Dashboard", JOptionPane.ERROR_MESSAGE);
    }

    @Override
    public void onDataLoaded() {
        SwingUtilities.invokeLater(() -> {
            refreshDashboard();
            refreshStudentsManagerRows();
            refreshAttendanceSelectors();
            refreshAttendanceRows();
        });
    }

    @Override
    public void onSessionChanged(SessionInfo session) {
        SwingUtilities.invokeLater(this::refreshDashboard);
    }

    @Override
    public void onSubjectAdded(Subject subject) {
        SwingUtilities.invokeLater(() -> {
            refreshDashboard();
            refreshAttendanceSelectors();
            refreshAttendanceRows();
        });
    }

    @Override
    public void onDailyAttendanceChanged(java.time.LocalDate date, Boolean attended) {
        SwingUtilities.invokeLater(this::refreshDashboard);
    }

    @Override
    public void onTeacherDataChanged() {
        SwingUtilities.invokeLater(() -> {
            refreshDashboard();
            refreshStudentsManagerRows();
            refreshAttendanceSelectors();
            refreshAttendanceRows();
        });
    }
}
