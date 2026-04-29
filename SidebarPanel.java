import java.awt.*;
import javax.swing.*;

public class SidebarPanel extends JPanel {
    private final java.util.Map<String, JButton> navButtons = new java.util.HashMap<>();
    private final Color normal = new Color(15, 35, 120);
    private final Color hover = new Color(35, 60, 150);
    private final Color active = new Color(45, 75, 170);

    public SidebarPanel(MainPanel main) {
        setPreferredSize(new Dimension(220, 0));
        setMinimumSize(new Dimension(220, 0));
        setBackground(normal);
        setLayout(new BoxLayout(this, BoxLayout.Y_AXIS));

        add(Box.createVerticalStrut(20));
        add(navButton("Dashboard", "dashboard", main));
        add(Box.createRigidArea(new Dimension(0, 4)));
        add(navButton("Attendance", "attendance", main));
        add(Box.createRigidArea(new Dimension(0, 4)));
        add(navButton("Profile", "profile", main));
        setActive("dashboard");
        add(Box.createVerticalGlue());
        add(button("Logout", e -> {
            try {
                new ModernLoginUI();
                SwingUtilities.getWindowAncestor(this).dispose();
            } catch (Exception ex) {
                JOptionPane.showMessageDialog(this, "Logout error: " + ex.getMessage());
            }
        }));
    }

    private void safeShow(MainPanel main, String panel) {
        try {
            main.showPanel(panel);
            setActive(panel);
        }
        catch (Exception ex) {
            JOptionPane.showMessageDialog(this, "Navigation error: " + ex.getMessage());
        }
    }

    private JButton navButton(String text, String panel, MainPanel main) {
        JButton btn = button(text, e -> safeShow(main, panel));
        navButtons.put(panel, btn);
        return btn;
    }

    private void setActive(String panel) {
        for (java.util.Map.Entry<String, JButton> entry : navButtons.entrySet()) {
            JButton button = entry.getValue();
            button.setBackground(entry.getKey().equals(panel) ? active : normal);
        }
    }

    private JButton button(String text, java.awt.event.ActionListener action) {
        JButton btn = new JButton(text);
        btn.setMaximumSize(new Dimension(200, 40));
        btn.setForeground(Color.WHITE);
        btn.setBackground(normal);
        btn.setFocusPainted(false);
        btn.addMouseListener(new java.awt.event.MouseAdapter() {
            @Override public void mouseEntered(java.awt.event.MouseEvent e) {
                if (!navButtons.containsValue(btn) || btn.getBackground().equals(normal)) btn.setBackground(hover);
            }
            @Override public void mouseExited(java.awt.event.MouseEvent e) {
                if (!navButtons.containsValue(btn) || btn.getBackground().equals(hover)) btn.setBackground(normal);
            }
        });
        btn.addActionListener(action);
        return btn;
    }
}
