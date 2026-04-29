import java.io.*;
import java.util.logging.*;
import javax.swing.JOptionPane;

public class DataStore {

    private static final String DATA_FILE = "attendance_data.ser";
    private static final Logger LOGGER    = Logger.getLogger(DataStore.class.getName());

    private DataStore() {}

    public static AppData load() {
        File file = new File(DATA_FILE);

        if (!file.exists()) {
            LOGGER.info("No saved data found — starting fresh.");
            return new AppData();
        }

        try (ObjectInputStream ois =
                 new ObjectInputStream(new FileInputStream(file))) {

            AppData data = (AppData) ois.readObject();
            LOGGER.info("Data loaded successfully from " + DATA_FILE);
            return data;

        } catch (InvalidClassException e) {

            LOGGER.warning("Saved data format outdated, resetting: " + e.getMessage());
            file.delete();
            return new AppData();

        } catch (IOException e) {
            LOGGER.severe("IO error loading data: " + e.getMessage());
            showError("Could not read saved data.\nStarting with a clean slate.\n\nDetail: " + e.getMessage());
            return new AppData();

        } catch (ClassNotFoundException e) {
            LOGGER.severe("Class not found during deserialization: " + e.getMessage());
            return new AppData();
        }
    }

    public static void save(AppData data) {
        if (data == null) {
            LOGGER.warning("Attempted to save null AppData — skipped.");
            return;
        }

        try (ObjectOutputStream oos =
                 new ObjectOutputStream(new FileOutputStream(DATA_FILE))) {

            oos.writeObject(data);
            LOGGER.info("Data saved successfully to " + DATA_FILE);

        } catch (IOException e) {
            LOGGER.severe("IO error saving data: " + e.getMessage());
            showError("Could not save data to disk.\nYour changes may be lost on restart.\n\nDetail: " + e.getMessage());
        }
    }

    private static void showError(String message) {

        try {
            javax.swing.SwingUtilities.invokeLater(() ->
                JOptionPane.showMessageDialog(null, message, "Storage Error",
                    JOptionPane.WARNING_MESSAGE));
        } catch (Exception ignored) {  }
    }
}
