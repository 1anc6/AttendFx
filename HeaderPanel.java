import java.awt.*;
import javax.swing.*;

public class HeaderPanel extends JPanel {

    public HeaderPanel() {
        setLayout(new BorderLayout());
        setPreferredSize(new Dimension(1000, 70));
        setBackground(new Color(245, 245, 245));
        setBorder(BorderFactory.createEmptyBorder(10, 20, 10, 20));

        JTextField search = new JTextField(" Search for student...");
        search.setPreferredSize(new Dimension(400, 35));
        search.setBorder(BorderFactory.createEmptyBorder(5, 10, 5, 10));
        add(search, BorderLayout.CENTER);
    }
}
