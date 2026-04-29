import java.awt.*;
import javax.swing.*;

public class ShadowPanel extends JPanel {

    public ShadowPanel(LayoutManager layout) {
        setLayout(layout);
        setOpaque(false);
    }

    @Override
    protected void paintComponent(Graphics g) {
        Graphics2D g2 = (Graphics2D) g;
        for (int i = 0; i < 6; i++) {
            g2.setColor(new Color(0, 0, 0, 20));
            g2.drawRoundRect(i, i, getWidth() - i * 2, getHeight() - i * 2, 20, 20);
        }
        super.paintComponent(g);
    }
}
