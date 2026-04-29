import java.awt.*;
import javax.swing.*;

public class RoundedPanel extends JPanel {

    private final int   radius;
    private final Color bgColor;

    public RoundedPanel(int radius, Color color) {
        this.radius  = radius;
        this.bgColor = color;
        setOpaque(false);
    }

    @Override
    protected void paintComponent(Graphics g) {
        Graphics2D g2 = (Graphics2D) g;
        g2.setRenderingHint(RenderingHints.KEY_ANTIALIASING, RenderingHints.VALUE_ANTIALIAS_ON);
        g2.setColor(bgColor);
        g2.fillRoundRect(0, 0, getWidth(), getHeight(), radius, radius);
        super.paintComponent(g);
    }
}
