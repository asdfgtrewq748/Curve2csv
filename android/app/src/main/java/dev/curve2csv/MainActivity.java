package dev.curve2csv;

import android.content.Intent;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.view.MotionEvent;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.TextView;
import androidx.activity.result.ActivityResultLauncher;
import androidx.activity.result.contract.ActivityResultContracts;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.FileProvider;
import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONObject;

/** Photo or gallery, a two-tap crop, typed axis endpoints, then CSV share. */
public class MainActivity extends AppCompatActivity {
    private static final String TAG = "Curve2csv";

    private ImageView figureView;
    private ImageView overlayView;
    private TextView statusView;
    private Bitmap figure;
    private File imageFile;
    private File csvFile;
    private float cropX = Float.NaN;
    private float cropY = Float.NaN;
    private final ExecutorService worker = Executors.newSingleThreadExecutor();

    private final ActivityResultLauncher<Uri> camera =
            registerForActivityResult(new ActivityResultContracts.TakePicture(), ok -> {
                if (Boolean.TRUE.equals(ok) && imageFile != null) {
                    showFile(imageFile);
                }
            });

    private final ActivityResultLauncher<String> gallery =
            registerForActivityResult(new ActivityResultContracts.GetContent(), uri -> {
                if (uri != null) {
                    loadUri(uri);
                }
            });

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (!Python.isStarted()) {
            Python.start(new AndroidPlatform(this));
        }
        if (getIntent().getBooleanExtra("smoke", false)) {
            runSmoke();
            return;
        }
        setContentView(R.layout.activity_main);
        figureView = findViewById(R.id.figure);
        overlayView = findViewById(R.id.overlay);
        statusView = findViewById(R.id.status);
        Button takePhoto = findViewById(R.id.take_photo);
        Button pickImage = findViewById(R.id.pick_image);
        Button extract = findViewById(R.id.extract);
        Button share = findViewById(R.id.share);
        takePhoto.setOnClickListener(v -> launchCamera());
        pickImage.setOnClickListener(v -> gallery.launch("image/*"));
        extract.setOnClickListener(v -> runExtract());
        share.setOnClickListener(v -> shareCsv());
        figureView.setOnTouchListener((view, event) -> {
            if (event.getAction() == MotionEvent.ACTION_UP) {
                onFigureTap(event.getX(), event.getY());
            }
            return true;
        });
    }

    private void launchCamera() {
        try {
            imageFile = File.createTempFile("capture", ".jpg", getCacheDir());
            Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".files", imageFile);
            camera.launch(uri);
        } catch (Exception exc) {
            setStatus(exc.getMessage());
        }
    }

    private void loadUri(Uri uri) {
        try (InputStream stream = getContentResolver().openInputStream(uri)) {
            Bitmap bitmap = BitmapFactory.decodeStream(stream);
            if (bitmap == null) {
                setStatus("Could not read that image.");
                return;
            }
            imageFile = File.createTempFile("picked", ".png", getCacheDir());
            try (FileOutputStream out = new FileOutputStream(imageFile)) {
                bitmap.compress(Bitmap.CompressFormat.PNG, 100, out);
            }
            showFile(imageFile);
        } catch (Exception exc) {
            setStatus(exc.getMessage());
        }
    }

    private void showFile(File file) {
        figure = BitmapFactory.decodeFile(file.getAbsolutePath());
        figureView.setImageBitmap(figure);
        overlayView.setImageDrawable(null);
        csvFile = null;
        cropX = Float.NaN;
        setStatus("Image ready. Type the axis endpoints, then extract.");
    }

    private void onFigureTap(float x, float y) {
        if (figure == null) {
            return;
        }
        float[] bitmapPoint = toBitmap(x, y);
        if (bitmapPoint == null) {
            return;
        }
        if (Float.isNaN(cropX)) {
            cropX = bitmapPoint[0];
            cropY = bitmapPoint[1];
            setStatus("First corner set. Tap the opposite corner to crop.");
            return;
        }
        int left = Math.max(0, Math.round(Math.min(cropX, bitmapPoint[0])));
        int top = Math.max(0, Math.round(Math.min(cropY, bitmapPoint[1])));
        int right = Math.min(figure.getWidth(), Math.round(Math.max(cropX, bitmapPoint[0])));
        int bottom = Math.min(figure.getHeight(), Math.round(Math.max(cropY, bitmapPoint[1])));
        cropX = Float.NaN;
        if (right - left < 20 || bottom - top < 20) {
            setStatus("That crop is too small. Tap two corners of the figure.");
            return;
        }
        figure = Bitmap.createBitmap(figure, left, top, right - left, bottom - top);
        try {
            imageFile = File.createTempFile("crop", ".png", getCacheDir());
            try (FileOutputStream out = new FileOutputStream(imageFile)) {
                figure.compress(Bitmap.CompressFormat.PNG, 100, out);
            }
            figureView.setImageBitmap(figure);
            setStatus("Cropped to the figure.");
        } catch (Exception exc) {
            setStatus(exc.getMessage());
        }
    }

    /** Map a tap on the fitCenter ImageView back to bitmap pixels. */
    private float[] toBitmap(float viewX, float viewY) {
        float viewW = figureView.getWidth();
        float viewH = figureView.getHeight();
        float scale = Math.min(viewW / figure.getWidth(), viewH / figure.getHeight());
        float drawnW = figure.getWidth() * scale;
        float drawnH = figure.getHeight() * scale;
        float left = (viewW - drawnW) / 2f;
        float top = (viewH - drawnH) / 2f;
        float bx = (viewX - left) / scale;
        float by = (viewY - top) / scale;
        if (bx < 0 || by < 0 || bx >= figure.getWidth() || by >= figure.getHeight()) {
            return null;
        }
        return new float[] {bx, by};
    }

    private void runExtract() {
        if (imageFile == null) {
            setStatus("Choose a photo or an image first.");
            return;
        }
        double xmin;
        double xmax;
        double ymin;
        double ymax;
        try {
            xmin = number(R.id.xmin);
            xmax = number(R.id.xmax);
            ymin = number(R.id.ymin);
            ymax = number(R.id.ymax);
        } catch (NumberFormatException exc) {
            setStatus("Axis values must be numbers.");
            return;
        }
        boolean xLog = ((CheckBox) findViewById(R.id.x_log)).isChecked();
        boolean yLog = ((CheckBox) findViewById(R.id.y_log)).isChecked();
        setStatus("Extracting on the device…");
        File source = imageFile;
        worker.execute(() -> {
            String raw = callDigitize(source, xmin, xmax, ymin, ymax, xLog, yLog);
            runOnUiThread(() -> showResult(raw));
        });
    }

    private double number(int id) {
        return Double.parseDouble(((EditText) findViewById(id)).getText().toString().trim());
    }

    private String callDigitize(
            File source, double xmin, double xmax, double ymin, double ymax, boolean xLog, boolean yLog) {
        File out = new File(getCacheDir(), "extract");
        if (!out.isDirectory() && !out.mkdirs()) {
            return "{\"ok\":false,\"error\":\"could not create the output directory\"}";
        }
        PyObject module = Python.getInstance().getModule("curve2csv_android");
        return module.callAttr(
                        "digitize",
                        source.getAbsolutePath(),
                        out.getAbsolutePath(),
                        xmin,
                        xmax,
                        ymin,
                        ymax,
                        xLog,
                        yLog)
                .toString();
    }

    private void showResult(String raw) {
        try {
            JSONObject payload = new JSONObject(raw);
            if (!payload.optBoolean("ok")) {
                setStatus(payload.optString("error", "Extraction failed."));
                return;
            }
            csvFile = new File(payload.getString("csv"));
            Bitmap overlay = BitmapFactory.decodeFile(payload.getString("overlay"));
            overlayView.setImageBitmap(overlay);
            setStatus(
                    "Series "
                            + payload.optInt("n_series")
                            + ", points "
                            + payload.optInt("n_points")
                            + ". Correct the axis numbers and extract again, or share the CSV.");
        } catch (Exception exc) {
            setStatus(raw);
        }
    }

    private void shareCsv() {
        if (csvFile == null || !csvFile.isFile()) {
            setStatus("Extract a figure before sharing.");
            return;
        }
        Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".files", csvFile);
        Intent send = new Intent(Intent.ACTION_SEND);
        send.setType("text/csv");
        send.putExtra(Intent.EXTRA_STREAM, uri);
        send.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
        startActivity(Intent.createChooser(send, "Share CSV"));
    }

    private void setStatus(String text) {
        if (statusView != null) {
            statusView.setText(text == null ? "" : text);
        }
    }

    /** Headless check used by CI: one bundled figure, fixed limits, a CSV on disk. */
    private void runSmoke() {
        try {
            File image = new File(getCacheDir(), "smoke.png");
            try (InputStream stream = getAssets().open("smoke.png");
                    FileOutputStream out = new FileOutputStream(image)) {
                byte[] buffer = new byte[8192];
                int read;
                while ((read = stream.read(buffer)) >= 0) {
                    out.write(buffer, 0, read);
                }
            }
            String raw = callDigitize(image, 0.0, 3.0, -1.2, 1.2, false, false);
            JSONObject payload = new JSONObject(raw);
            File csv = new File(payload.getString("csv"));
            if (!payload.optBoolean("ok") || !csv.isFile() || csv.length() == 0) {
                Log.e(TAG, "SMOKE_FAIL " + raw);
            } else {
                Log.i(TAG, "SMOKE_OK series=" + payload.optInt("n_series"));
            }
        } catch (Exception exc) {
            Log.e(TAG, "SMOKE_FAIL " + exc);
        }
        finish();
    }
}
