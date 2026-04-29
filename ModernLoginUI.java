import java.awt.*;
import java.awt.event.*;
import javax.swing.*;

public class ModernLoginUI extends JFrame {

    public ModernLoginUI() {
        setTitle("Attendance Login");
        setSize(900, 600);
        setLocationRelativeTo(null);
        setDefaultCloseOperation(JFrame.EXIT_ON_CLOSE);

        ImageBackgroundPanel background = new ImageBackgroundPanel("bg.jpg");
        background.setLayout(new GridBagLayout());

        JPanel container = new JPanel(new GridLayout(1, 2));
        container.setOpaque(false);
        container.setPreferredSize(new Dimension(800, 500));

        container.add(createLoginCard());
        container.add(createRightPanel());

        background.add(container);
        setContentPane(background);
        setVisible(true);
    }

    private JPanel createLoginCard() {
        RoundedPanel card = new RoundedPanel(30);
        card.setOpaque(false);
        card.setLayout(null);
        card.setPreferredSize(new Dimension(400, 500));

        JLabel title = new JLabel("Attendance Login");
        title.setFont(new Font("Segoe UI", Font.BOLD, 28));
        title.setForeground(Color.WHITE);
        title.setBounds(100, 50, 250, 40);
        card.add(title);

        JLabel emailLabel = new JLabel("Username");
        emailLabel.setForeground(Color.WHITE);
        emailLabel.setBounds(50, 120, 300, 20);
        card.add(emailLabel);

        RoundedTextField emailField = new RoundedTextField(20);
        emailField.setBounds(50, 145, 300, 40);
        card.add(emailField);

        JLabel passLabel = new JLabel("Password");
        passLabel.setForeground(Color.WHITE);
        passLabel.setBounds(50, 200, 300, 20);
        card.add(passLabel);

        RoundedPasswordField passField = new RoundedPasswordField(20);
        passField.setBounds(50, 225, 300, 40);
        card.add(passField);

        RoundedButton loginBtn = new RoundedButton("Login");
        loginBtn.setBounds(50, 300, 300, 45);
        card.add(loginBtn);

        RoundedButton signupBtn = new RoundedButton("Sign Up");
        signupBtn.setBounds(50, 360, 300, 45);
        card.add(signupBtn);

        passField.addActionListener(e -> loginBtn.doClick());

        loginBtn.addActionListener(e -> {
            try {
                String username = emailField.getText().trim();
                String password = new String(passField.getPassword()).trim();

                if (username.isEmpty() || password.isEmpty()) {
                    JOptionPane.showMessageDialog(this, "Please enter both username and password.",
                        "Login Error", JOptionPane.WARNING_MESSAGE);
                    return;
                }

                AttendanceService service = AttendanceService.getInstance();
                if (service.isTeacherLogin(username, password)) {
                    new TeacherDashboard(username);
                    dispose();
                } else if (service.isStudentLogin(username, password)) {
                    new StudentDashboard(username);
                    dispose();
                } else {
                    JOptionPane.showMessageDialog(this, "Invalid username or password.",
                        "Login Failed", JOptionPane.ERROR_MESSAGE);
                    passField.setText("");
                }
            } catch (Exception ex) {
                JOptionPane.showMessageDialog(this, "Unexpected error: " + ex.getMessage(),
                    "Error", JOptionPane.ERROR_MESSAGE);
            }
        });

        signupBtn.addActionListener(e -> {
            try {
                new SignupUI();
                dispose();
            } catch (Exception ex) {
                JOptionPane.showMessageDialog(this, "Could not open signup: " + ex.getMessage(),
                    "Navigation Error", JOptionPane.ERROR_MESSAGE);
            }
        });

        return card;
    }

    private JPanel createRightPanel() {
        JPanel panel = new JPanel();
        panel.setOpaque(false);
        panel.setLayout(null);

        JLabel text = new JLabel("<html><center>Welcome Back<br>Login to Continue</center></html>");
        text.setFont(new Font("Segoe UI", Font.BOLD, 26));
        text.setForeground(Color.WHITE);
        text.setBounds(50, 80, 320, 120);
        panel.add(text);
        return panel;
    }

    class ImageBackgroundPanel extends JPanel {
        private Image image;

        ImageBackgroundPanel(String path) {
            try {
                ImageIcon icon = new ImageIcon(path);
                image = icon.getImage();
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

                GradientPaint gp = new GradientPaint(
                    0, 0, new Color(15, 35, 120),
                    getWidth(), getHeight(), new Color(80, 100, 200));
                g2.setPaint(gp);
                g2.fillRect(0, 0, getWidth(), getHeight());
            }
            g2.setColor(new Color(0, 0, 0, 80));
            g2.fillRect(0, 0, getWidth(), getHeight());
        }
    }

    class RoundedPanel extends JPanel {
        private final int radius;
        RoundedPanel(int radius) { this.radius = radius; setOpaque(false); }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
            int w = getWidth(), h = getHeight();
            g2.setColor(new Color(0, 0, 0, 80));
            g2.fillRoundRect(10, 10, w - 10, h - 10, radius, radius);
            g2.setColor(new Color(255, 255, 255, 40));
            g2.fillRoundRect(0, 0, w - 10, h - 10, radius, radius);
            g2.setColor(new Color(255, 255, 255, 120));
            g2.drawRoundRect(0, 0, w - 10, h - 10, radius, radius);
            g2.dispose();
            super.paintComponent(g);
        }
    }

    class RoundedTextField extends JTextField {
        int radius;
        RoundedTextField(int r) { radius = r; setOpaque(false); setBorder(BorderFactory.createEmptyBorder(5, 15, 5, 15)); }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setColor(new Color(255, 255, 255, 80));
            g2.fillRoundRect(0, 0, getWidth(), getHeight(), radius, radius);
            g2.dispose();
            super.paintComponent(g);
        }
    }

    class RoundedPasswordField extends JPasswordField {
        int radius;
        RoundedPasswordField(int r) { radius = r; setOpaque(false); setBorder(BorderFactory.createEmptyBorder(5, 15, 5, 15)); }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setColor(new Color(255, 255, 255, 80));
            g2.fillRoundRect(0, 0, getWidth(), getHeight(), radius, radius);
            g2.dispose();
            super.paintComponent(g);
        }
    }

    class RoundedButton extends JButton {
        Color normal = new Color(115, 120, 255);
        Color hover  = new Color(90, 95, 240);

        RoundedButton(String text) {
            super(text);
            setForeground(Color.WHITE);
            setFocusPainted(false);
            setContentAreaFilled(false);
            setCursor(new Cursor(Cursor.HAND_CURSOR));
            setBackground(normal);
            addMouseListener(new MouseAdapter() {
                @Override public void mouseEntered(MouseEvent e) { setBackground(hover); }
                @Override public void mouseExited(MouseEvent e)  { setBackground(normal); }
            });
        }

        @Override
        protected void paintComponent(Graphics g) {
            Graphics2D g2 = (Graphics2D) g.create();
            g2.setColor(getBackground());
            g2.fillRoundRect(0, 0, getWidth(), getHeight(), 20, 20);
            g2.dispose();
            super.paintComponent(g);
        }
    }
}
