import java.awt.*;
import javax.swing.*;

public class PerformancePanel extends JPanel {

    private int performance = 0;

    public PerformancePanel() {
        setBorder(BorderFactory.createTitledBorder("Attendance Statistics"));
        setBackground(Color.WHITE);
    }

    public void updatePerformance(int value) {
        this.performance = Math.max(0, Math.min(100, value));
        repaint();
    }

    @Override
    protected void paintComponent(Graphics g) {
        super.paintComponent(g);
        Graphics2D g2 = (Graphics2D) g;
        g2.setStroke(new BasicStroke(15));
        g2.setColor(Color.LIGHT_GRAY);
        g2.drawArc(50, 50, 200, 200, 0, 360);
        g2.setColor(new Color(255, 180, 0));
        g2.drawArc(50, 50, 200, 200, 90, -(performance * 360 / 100));
        g2.setFont(new Font("Segoe UI", Font.BOLD, 30));
        g2.drawString(performance + "%", 120, 170);
        g2.setFont(new Font("Segoe UI", Font.PLAIN, 16));
        g2.drawString("Overall Attendance", 85, 220);
    }
}
