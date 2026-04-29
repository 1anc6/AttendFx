import java.awt.*;
import javax.swing.*;
import javax.swing.border.Border;

public class ProfilePanel extends JPanel implements AttendanceChangeListener {

    private final AttendanceService service = AttendanceService.getInstance();
    private static final Dimension BASIC_FIELD_SIZE = new Dimension(300, 38);
    private static final Dimension DETAIL_FIELD_SIZE = new Dimension(250, 36);
    private static final Dimension FIELD_MAX_SIZE = new Dimension(Integer.MAX_VALUE, 40);
    private final Border normalBorder = BorderFactory.createCompoundBorder(
        BorderFactory.createLineBorder(new Color(200, 200, 200)),
        BorderFactory.createEmptyBorder(4, 8, 4, 8)
    );
    private final Border activeBorder = BorderFactory.createCompoundBorder(
        BorderFactory.createLineBorder(new Color(80, 115, 245), 2),
        BorderFactory.createEmptyBorder(3, 7, 3, 7)
    );

    private AvatarLabel avatarLabel;
    private JLabel titleLabel;
    private JLabel subtitleLabel;
    private JTextField nameField;
    private JTextField universityRollField;
    private JTextField classRollField;
    private JTextField sectionField;
    private JTextField courseField;
    private JTextField emailField;
    private JTextField phoneField;
    private JTextField addressField;
    private JTextField dobField;
    private JButton editBtn;
    private JButton saveBtn;
    private JButton cancelBtn;

    public ProfilePanel() {
        service.addListener(this);
        setLayout(new BorderLayout());
        setBackground(new Color(240, 242, 245));

        JPanel content = new JPanel();
        content.setLayout(new BoxLayout(content, BoxLayout.Y_AXIS));
        content.setBackground(new Color(240, 242, 245));
        content.setBorder(BorderFactory.createEmptyBorder(24, 24, 24, 24));

        JPanel header = createHeader();
        JPanel details = createDetails();
        header.setAlignmentX(Component.LEFT_ALIGNMENT);
        details.setAlignmentX(Component.LEFT_ALIGNMENT);
        header.setMaximumSize(new Dimension(Integer.MAX_VALUE, header.getPreferredSize().height));
        details.setMaximumSize(new Dimension(Integer.MAX_VALUE, Integer.MAX_VALUE));

        content.add(header);
        content.add(Box.createRigidArea(new Dimension(0, 18)));
        content.add(details);

        add(content, BorderLayout.CENTER);
        setEditing(false);
        refreshProfile();
    }

    private JPanel createHeader() {
        RoundedPanel header = new RoundedPanel(20, new Color(255, 255, 255));
        header.setLayout(new BorderLayout(18, 0));
        header.setBorder(BorderFactory.createEmptyBorder(22, 28, 22, 28));

        avatarLabel = new AvatarLabel("S");
        avatarLabel.setPreferredSize(new Dimension(84, 84));

        JPanel text = new JPanel(new GridLayout(2, 1));
        text.setOpaque(false);
        titleLabel = new JLabel("Student");
        titleLabel.setFont(new Font("Segoe UI", Font.BOLD, 30));
        subtitleLabel = new JLabel("Student");
        subtitleLabel.setFont(new Font("Segoe UI", Font.PLAIN, 16));
        subtitleLabel.setForeground(new Color(80, 80, 90));

        text.add(titleLabel);
        text.add(subtitleLabel);
        header.add(avatarLabel, BorderLayout.WEST);
        header.add(text, BorderLayout.CENTER);

        editBtn = actionButton("Edit");
        editBtn.addActionListener(e -> setEditing(true));
        header.add(editBtn, BorderLayout.EAST);
        return wrapShadow(header);
    }

    private JPanel createDetails() {
        JPanel wrapper = new JPanel();
        wrapper.setLayout(new BoxLayout(wrapper, BoxLayout.Y_AXIS));
        wrapper.setOpaque(false);

        nameField = field("", BASIC_FIELD_SIZE);
        universityRollField = field("", BASIC_FIELD_SIZE);
        classRollField = field("", BASIC_FIELD_SIZE);
        sectionField = field("", BASIC_FIELD_SIZE);
        courseField = field("", BASIC_FIELD_SIZE);
        emailField = field("Enter email", DETAIL_FIELD_SIZE);
        phoneField = field("Enter phone number", DETAIL_FIELD_SIZE);
        addressField = field("Enter address", DETAIL_FIELD_SIZE);
        dobField = field("YYYY-MM-DD", DETAIL_FIELD_SIZE);

        JPanel basicInfo = sectionCard("\uD83D\uDC64  Basic Info", new String[] {
            "Name", "University Roll No", "Class Roll No", "Section", "Course"
        }, new JTextField[] {
            nameField, universityRollField, classRollField, sectionField, courseField
        }, false, 82, new Insets(12, 18, 12, 18), 18);

        JPanel contactInfo = sectionCard("\uD83D\uDCDE  Contact Info", new String[] {
            "Email", "Phone Number"
        }, new JTextField[] {
            emailField, phoneField
        }, false, 64, new Insets(10, 18, 10, 18), 12);

        JPanel optionalDetails = sectionCard("\uD83D\uDCCD  Optional Details", new String[] {
            "Address", "Date of Birth"
        }, new JTextField[] {
            addressField, dobField
        }, true, 64, new Insets(10, 18, 10, 18), 12);

        addProfileSection(wrapper, basicInfo, 250);
        wrapper.add(Box.createRigidArea(new Dimension(0, 18)));
        addProfileSection(wrapper, contactInfo, 150);
        wrapper.add(Box.createRigidArea(new Dimension(0, 18)));
        addProfileSection(wrapper, optionalDetails, 190);
        wrapper.add(Box.createVerticalGlue());

        return wrapper;
    }

    private void addProfileSection(JPanel wrapper, JPanel section, int height) {
        section.setAlignmentX(Component.LEFT_ALIGNMENT);
        section.setPreferredSize(new Dimension(0, height));
        section.setMaximumSize(new Dimension(Integer.MAX_VALUE, height));
        wrapper.add(section);
    }

    private JPanel sectionCard(String title, String[] labels, JTextField[] fields, boolean includeButtons,
                               int groupHeight, Insets padding, int rowGap) {
        RoundedPanel card = new RoundedPanel(20, Color.WHITE);
        card.setLayout(new BorderLayout(10, 10));
        card.setBorder(BorderFactory.createEmptyBorder(
            padding.top, padding.left, padding.bottom, padding.right
        ));

        JLabel titleLabel = new JLabel(title);
        titleLabel.setFont(new Font("Segoe UI", Font.BOLD, 15));
        card.add(titleLabel, BorderLayout.NORTH);

        JPanel grid = new JPanel(new GridLayout(0, 2, 18, rowGap));
        grid.setOpaque(false);
        for (int i = 0; i < labels.length; i++) {
            grid.add(fieldGroup(labels[i], fields[i], groupHeight));
        }
        if (labels.length % 2 != 0) {
            JPanel spacer = new JPanel();
            spacer.setOpaque(false);
            grid.add(spacer);
        }
        card.add(grid, BorderLayout.CENTER);

        if (includeButtons) {
            JPanel buttons = new JPanel(new FlowLayout(FlowLayout.RIGHT, 10, 0));
            buttons.setOpaque(false);
            saveBtn = actionButton("Save");
            cancelBtn = actionButton("Cancel");
            saveBtn.addActionListener(e -> saveProfile());
            cancelBtn.addActionListener(e -> {
                refreshProfile();
                setEditing(false);
            });
            buttons.add(cancelBtn);
            buttons.add(saveBtn);
            card.add(buttons, BorderLayout.SOUTH);
        }

        return wrapShadow(card);
    }

    private JPanel fieldGroup(String label, JTextField field, int height) {
        JPanel group = new JPanel();
        group.setLayout(new BoxLayout(group, BoxLayout.Y_AXIS));
        group.setOpaque(false);
        group.setPreferredSize(new Dimension(300, height));
        group.setMinimumSize(new Dimension(180, height));
        JLabel l = new JLabel(label);
        l.setFont(new Font("Segoe UI", Font.PLAIN, 12));
        l.setForeground(new Color(120, 120, 120));
        l.setAlignmentX(Component.LEFT_ALIGNMENT);
        field.setAlignmentX(Component.LEFT_ALIGNMENT);
        group.add(l);
        group.add(Box.createRigidArea(new Dimension(0, 6)));
        group.add(field);
        group.add(Box.createVerticalGlue());
        return group;
    }

    private JTextField field(String placeholder, Dimension size) {
        JTextField field = new JTextField();
        field.setToolTipText(placeholder);
        field.setBorder(normalBorder);
        field.setFont(new Font("Segoe UI", Font.BOLD, 16));
        field.setForeground(new Color(30, 30, 30));
        field.setCaretColor(new Color(30, 30, 30));
        field.setPreferredSize(size);
        field.setMinimumSize(new Dimension(180, size.height));
        field.setMaximumSize(FIELD_MAX_SIZE);
        field.addFocusListener(new java.awt.event.FocusAdapter() {
            @Override public void focusGained(java.awt.event.FocusEvent e) {
                if (field.isEditable()) field.setBorder(activeBorder);
            }
            @Override public void focusLost(java.awt.event.FocusEvent e) {
                field.setBorder(normalBorder);
            }
        });
        return field;
    }

    private JButton actionButton(String text) {
        JButton button = new JButton(text);
        button.setPreferredSize(new Dimension(96, 38));
        button.setForeground(Color.WHITE);
        button.setBackground(new Color(115, 120, 255));
        button.setFocusPainted(false);
        button.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override public void mouseEntered(java.awt.event.MouseEvent e) { button.setBackground(new Color(90, 95, 240)); }
            @Override public void mouseExited(java.awt.event.MouseEvent e) { button.setBackground(new Color(115, 120, 255)); }
        });
        return button;
    }

    private JPanel wrapShadow(JPanel panel) {
        ShadowPanel shadow = new ShadowPanel(new BorderLayout());
        shadow.add(panel, BorderLayout.CENTER);
        return shadow;
    }

    public void refreshProfile() {
        StudentRecord student = service.getCurrentStudentProfile();
        if (student == null) {
            titleLabel.setText("Student");
            avatarLabel.setInitial("S");
            setText(nameField, "");
            setText(universityRollField, "");
            setText(classRollField, "");
            setText(sectionField, "");
            setText(courseField, "");
            setText(emailField, "");
            setText(phoneField, "");
            setText(addressField, "");
            setText(dobField, "");
            return;
        }

        System.out.println(student);
        System.out.println("Profile load name: " + student.name);
        System.out.println("Profile load course: " + student.course);
        System.out.println("Profile Basic Info: name=" + student.name
            + ", universityRollNo=" + student.universityRollNo
            + ", classRollNo=" + student.classRollNo
            + ", section=" + student.section
            + ", course=" + student.course);

        String displayName = displayName(student);
        titleLabel.setText(displayName);
        subtitleLabel.setText("Student");
        avatarLabel.setInitial(displayName.substring(0, 1).toUpperCase());
        setText(nameField, displayName);
        setText(universityRollField, student.universityRollNo);
        setText(classRollField, student.classRollNo);
        setText(sectionField, student.section);
        setText(courseField, student.course);
        setText(emailField, student.email);
        setText(phoneField, student.phone);
        setText(addressField, student.address);
        setText(dobField, student.dateOfBirth);
    }

    private void saveProfile() {
        String error = service.updateCurrentStudentProfile(
            nameField.getText(),
            universityRollField.getText(),
            classRollField.getText(),
            sectionField.getText(),
            courseField.getText(),
            emailField.getText(),
            phoneField.getText(),
            addressField.getText(),
            dobField.getText()
        );

        if (error != null) {
            JOptionPane.showMessageDialog(this, error, "Profile Error", JOptionPane.ERROR_MESSAGE);
            return;
        }

        refreshProfile();
        setEditing(false);
        JOptionPane.showMessageDialog(this, "Profile updated successfully");
    }

    private void setEditing(boolean editing) {
        JTextField[] fields = {
            nameField, universityRollField, classRollField, sectionField, courseField,
            emailField, phoneField, addressField, dobField
        };
        for (JTextField field : fields) {
            field.setEnabled(true);
            field.setEditable(editing);
            field.setDisabledTextColor(new Color(30, 30, 30));
            field.setBackground(editing ? Color.WHITE : new Color(248, 250, 252));
            field.setBorder(normalBorder);
        }
        editBtn.setVisible(!editing);
        saveBtn.setVisible(editing);
        cancelBtn.setVisible(editing);
    }

    private void setText(JTextField field, String value) {
        field.setText(value == null ? "" : value);
        field.revalidate();
        field.repaint();
    }

    private String safe(String value) {
        return value == null || value.trim().isEmpty() ? "Student" : value.trim();
    }

    private String displayName(StudentRecord student) {
        String name = safe(student.name);
        String roll = student.universityRollNo == null ? "" : student.universityRollNo.trim();
        if (!roll.isEmpty() && name.endsWith(roll)) {
            String prefix = name.substring(0, name.length() - roll.length());
            if (prefix.length() > 0 && prefix.length() % 2 == 0) {
                String first = prefix.substring(0, prefix.length() / 2);
                String second = prefix.substring(prefix.length() / 2);
                if (first.equals(second)) return second + roll;
            }
        }
        if (name.length() % 2 == 0) {
            String first = name.substring(0, name.length() / 2);
            String second = name.substring(name.length() / 2);
            if (first.equals(second)) return first;
        }
        return name;
    }

    private static class AvatarLabel extends JLabel {
        AvatarLabel(String initial) {
            super(initial, SwingConstants.CENTER);
            setForeground(Color.WHITE);
            setFont(new Font("Segoe UI", Font.BOLD, 32));
        }

        void setInitial(String initial) {
            setText(initial == null || initial.isEmpty() ? "S" : initial);
            repaint();
        }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            GradientPaint gp = new GradientPaint(0, 0, new Color(15, 35, 120),
                getWidth(), getHeight(), new Color(115, 120, 255));
            g2.setPaint(gp);
            g2.fillOval(0, 0, getWidth(), getHeight());
            g2.dispose();
            super.paintComponent(g);
        }
    }

    @Override public void onDataLoaded() { SwingUtilities.invokeLater(this::refreshProfile); }
    @Override public void onSessionChanged(SessionInfo session) { }
    @Override public void onSubjectAdded(Subject subject) { }
    @Override public void onDailyAttendanceChanged(java.time.LocalDate date, Boolean attended) { }
    @Override public void onTeacherDataChanged() { SwingUtilities.invokeLater(this::refreshProfile); }
}
