import java.awt.*;
import javax.swing.*;

public class SignupUI extends JFrame {

    private final AttendanceService service = AttendanceService.getInstance();

    private JComboBox<String> roleBox;
    private JPanel fieldsPanel;

    private JTextField teacherUsernameField;
    private JPasswordField teacherPasswordField;

    private JTextField nameField;
    private JTextField universityRollField;
    private JTextField classRollField;
    private JTextField sectionField;
    private JTextField courseField;
    private JPasswordField studentPasswordField;

    public SignupUI() {
        setTitle("Attendance Signup");
        setSize(900, 600);
        setLocationRelativeTo(null);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);

        ImageBackgroundPanel background = new ImageBackgroundPanel("bg.jpg");
        background.setLayout(new GridBagLayout());
        background.add(createSignupCard());

        setContentPane(background);
        setVisible(true);
    }

    private JPanel createSignupCard() {
        RoundedPanel card = new RoundedPanel(30);
        card.setLayout(new BorderLayout(0, 16));
        card.setPreferredSize(new Dimension(560, 520));
        card.setBorder(BorderFactory.createEmptyBorder(28, 44, 28, 44));

        JLabel title = new JLabel("Create Account");
        title.setFont(new Font("Segoe UI", Font.BOLD, 28));
        title.setForeground(Color.WHITE);
        card.add(title, BorderLayout.NORTH);

        JPanel form = new JPanel(new BorderLayout(0, 12));
        form.setOpaque(false);

        roleBox = new JComboBox<>(new String[] {"Student", "Teacher"});
        roleBox.addActionListener(e -> rebuildRoleFields());
        form.add(row("Role", roleBox), BorderLayout.NORTH);

        fieldsPanel = new JPanel(new GridBagLayout());
        fieldsPanel.setOpaque(false);
        form.add(fieldsPanel, BorderLayout.CENTER);

        JPanel buttons = new JPanel(new GridLayout(1, 2, 16, 0));
        buttons.setOpaque(false);
        JButton back = button("Back to Login");
        JButton submit = button("Submit");
        back.addActionListener(e -> navigateToLogin());
        submit.addActionListener(e -> handleSubmit());
        buttons.add(back);
        buttons.add(submit);
        form.add(buttons, BorderLayout.SOUTH);

        card.add(form, BorderLayout.CENTER);
        rebuildRoleFields();
        return card;
    }

    private JPanel row(String label, JComponent field) {
        JPanel row = new JPanel(new BorderLayout(16, 0));
        row.setOpaque(false);

        JLabel lbl = new JLabel(label);
        lbl.setPreferredSize(new Dimension(160, 34));
        lbl.setForeground(Color.WHITE);
        lbl.setFont(new Font("Segoe UI", Font.BOLD, 13));

        field.setPreferredSize(new Dimension(260, 34));
        row.add(lbl, BorderLayout.WEST);
        row.add(field, BorderLayout.CENTER);
        return row;
    }

    private void rebuildRoleFields() {
        fieldsPanel.removeAll();
        clearFields();

        GridBagConstraints gbc = new GridBagConstraints();
        gbc.gridx = 0;
        gbc.weightx = 1.0;
        gbc.fill = GridBagConstraints.HORIZONTAL;
        gbc.insets = new Insets(6, 0, 6, 0);

        if ("Teacher".equals(roleBox.getSelectedItem())) {
            teacherUsernameField = new JTextField();
            teacherPasswordField = new JPasswordField();
            addDynamicRow(gbc, 0, "Username", teacherUsernameField);
            addDynamicRow(gbc, 1, "Password", teacherPasswordField);
        } else {
            nameField = new JTextField();
            universityRollField = new JTextField();
            classRollField = new JTextField();
            sectionField = new JTextField();
            courseField = new JTextField();
            studentPasswordField = new JPasswordField();

            addDynamicRow(gbc, 0, "Student Name", nameField);
            addDynamicRow(gbc, 1, "University Roll No", universityRollField);
            addDynamicRow(gbc, 2, "Class Roll No", classRollField);
            addDynamicRow(gbc, 3, "Section", sectionField);
            addDynamicRow(gbc, 4, "Course", courseField);
            addDynamicRow(gbc, 5, "Password", studentPasswordField);
        }

        fieldsPanel.revalidate();
        fieldsPanel.repaint();
    }

    private void addDynamicRow(GridBagConstraints gbc, int rowIndex, String label, JComponent field) {
        gbc.gridy = rowIndex;
        fieldsPanel.add(row(label, field), gbc);
    }

    private void clearFields() {
        teacherUsernameField = null;
        teacherPasswordField = null;
        nameField = null;
        universityRollField = null;
        classRollField = null;
        sectionField = null;
        courseField = null;
        studentPasswordField = null;
    }

    private JButton button(String text) {
        JButton btn = new JButton(text);
        btn.setForeground(Color.WHITE);
        btn.setBackground(new Color(115, 120, 255));
        btn.setFocusPainted(false);
        btn.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override public void mouseEntered(java.awt.event.MouseEvent e) {
                btn.setBackground(new Color(90, 95, 240));
            }
            @Override public void mouseExited(java.awt.event.MouseEvent e) {
                btn.setBackground(new Color(115, 120, 255));
            }
        });
        return btn;
    }

    private void handleSubmit() {
        try {
            if ("Teacher".equals(roleBox.getSelectedItem())) {
                handleTeacherSignup();
            } else {
                handleStudentSignup();
            }
        } catch (Exception ex) {
            showError("Signup failed: " + ex.getMessage());
        }
    }

    private void handleTeacherSignup() {
        String error = service.registerTeacher(
            teacherUsernameField.getText(),
            new String(teacherPasswordField.getPassword())
        );

        if (error != null) {
            showError(error);
            return;
        }

        showSuccessAndReturnToLogin();
    }

    private void handleStudentSignup() {
        String error = service.registerStudent(
            nameField.getText(),
            universityRollField.getText(),
            classRollField.getText(),
            sectionField.getText(),
            courseField.getText(),
            new String(studentPasswordField.getPassword())
        );

        if (error != null) {
            showError(error);
            return;
        }

        showSuccessAndReturnToLogin();
    }

    private void showSuccessAndReturnToLogin() {
        JOptionPane.showMessageDialog(
            this,
            "Signup Successful! Please login to continue.",
            "Success",
            JOptionPane.INFORMATION_MESSAGE
        );
        navigateToLogin();
    }

    private void navigateToLogin() {
        try {
            new ModernLoginUI();
            dispose();
        } catch (Exception ex) {
            showError("Navigation error: " + ex.getMessage());
        }
    }

    private void showError(String message) {
        JOptionPane.showMessageDialog(this, message, "Signup Error", JOptionPane.ERROR_MESSAGE);
    }

    class ImageBackgroundPanel extends JPanel {
        private Image image;

        ImageBackgroundPanel(String path) {
            try {
                image = new ImageIcon(path).getImage();
            } catch (Exception e) {
                image = null;
            }
        }

        @Override
        protected void paintComponent(Graphics g) {
            super.paintComponent(g);
            Graphics2D g2 = (Graphics2D) g;
            if (image != null) {
                g2.drawImage(image, 0, 0, getWidth(), getHeight(), this);
            } else {
                g2.setPaint(new GradientPaint(0, 0, new Color(15, 35, 120),
                    getWidth(), getHeight(), new Color(80, 100, 200)));
                g2.fillRect(0, 0, getWidth(), getHeight());
            }
            g2.setColor(new Color(0, 0, 0, 90));
            g2.fillRect(0, 0, getWidth(), getHeight());
        }
    }

    class RoundedPanel extends JPanel {
        private final int radius;

        RoundedPanel(int radius) {
            this.radius = radius;
            setOpaque(false);
        }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            g2.setColor(new Color(255, 255, 255, 45));
            g2.fillRoundRect(0, 0, getWidth(), getHeight(), radius, radius);
            g2.setColor(new Color(255, 255, 255, 130));
            g2.drawRoundRect(0, 0, getWidth() - 1, getHeight() - 1, radius, radius);
            g2.dispose();
            super.paintComponent(g);
        }
    }
}
