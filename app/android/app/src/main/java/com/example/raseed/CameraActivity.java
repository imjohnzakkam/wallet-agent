package com.example.raseed;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.widget.Button;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.camera.core.CameraSelector;
import androidx.camera.core.ImageCapture;
import androidx.camera.core.ImageCaptureException;
import androidx.camera.lifecycle.ProcessCameraProvider;
import androidx.camera.view.PreviewView;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.common.util.concurrent.ListenableFuture;
import com.google.gson.Gson;
import com.google.gson.JsonSyntaxException;

import java.io.File;
import java.io.IOException;
import java.io.Serializable;
import java.text.SimpleDateFormat;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

// Define a data class to hold the parsed OCR result
class OcrData implements Serializable {
    String user_id;
    String vendor_name;
    String category;
    String date_time;
    double amount;
    double subtotal;
    double tax;
    String currency;
    String payment_method;
    String language;
    List<Item> items;
    String created_at;

    static class Item implements Serializable {
        String name;
        double quantity;
        String unit;
        double price;
        String category;

        @Override
        public String toString() {
            return "Item{" +
                    "name='" + name + '\'' +
                    ", quantity=" + quantity +
                    ", unit='" + unit + '\'' +
                    ", price=" + price +
                    ", category='" + category + '\'' +
                    '}';
        }
    }

    @Override
    public String toString() {
        return "OcrData{" +
                "vendor_name='" + vendor_name + '\'' +
                ", date_time='" + date_time + '\'' +
                ", amount=" + amount +
                // Add other fields as needed for logging or display
                '}';
    }
}

public class CameraActivity extends AppCompatActivity {

    private static final int PERMISSION_REQUEST_CODE = 1001;
    private static final String TAG = "CameraActivity";

    private PreviewView previewView;
    private ImageCapture imageCapture;
    private ExecutorService cameraExecutor;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_camera);

        previewView = findViewById(R.id.previewView);
        Button captureButton = findViewById(R.id.captureButton);

        cameraExecutor = Executors.newSingleThreadExecutor();

        if (allPermissionsGranted()) {
            startCamera();
        } else {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.CAMERA},
                    PERMISSION_REQUEST_CODE);
        }

        captureButton.setOnClickListener(v -> takePhoto());
    }

    private boolean allPermissionsGranted() {
        return ContextCompat.checkSelfPermission(
                this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
    }

    private void startCamera() {
        ListenableFuture<ProcessCameraProvider> cameraProviderFuture =
                ProcessCameraProvider.getInstance(this);

        cameraProviderFuture.addListener(() -> {
            try {
                ProcessCameraProvider cameraProvider = cameraProviderFuture.get();

                androidx.camera.core.Preview preview = new androidx.camera.core.Preview.Builder().build();
                imageCapture = new ImageCapture.Builder().build();

                CameraSelector cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA;

                cameraProvider.unbindAll();
                cameraProvider.bindToLifecycle(
                        this,
                        cameraSelector,
                        preview,
                        imageCapture
                );

                preview.setSurfaceProvider(previewView.getSurfaceProvider());

            } catch (Exception e) {
                Log.e(TAG, "Error starting camera: ", e);
            }
        }, ContextCompat.getMainExecutor(this));
    }

    private void takePhoto() {
        if (imageCapture == null) return;

        File photoFile = new File(getExternalFilesDir(null),
                new SimpleDateFormat("yyyy-MM-dd-HH-mm-ss-SSS", Locale.US)
                        .format(System.currentTimeMillis()) + ".jpg");

        ImageCapture.OutputFileOptions outputOptions =
                new ImageCapture.OutputFileOptions.Builder(photoFile).build();

        imageCapture.takePicture(outputOptions, cameraExecutor,
                new ImageCapture.OnImageSavedCallback() {
                    @Override
                    public void onImageSaved(@NonNull ImageCapture.OutputFileResults output) {
                        Uri savedUri = Uri.fromFile(photoFile);
                        Log.d(TAG, "Photo capture succeeded: " + savedUri.toString());
                        uploadImage(photoFile);

                        runOnUiThread(() -> {
                            Toast.makeText(CameraActivity.this, "Photo saved", Toast.LENGTH_SHORT).show();

                            // Optional: Return photo URI to MainActivity or another screen
                            Intent resultIntent = new Intent();
                            // resultIntent.setData(savedUri); // No longer returning URI, as it's uploaded
                            setResult(RESULT_OK, resultIntent);
                            finish();
                        });
                    }

                    @Override
                    public void onError(@NonNull ImageCaptureException exception) {
                        Log.e(TAG, "Photo capture failed: " + exception.getMessage(), exception);
                        runOnUiThread(() -> Toast.makeText(CameraActivity.this, "Capture failed", Toast.LENGTH_SHORT).show());
                    }
                });
    }
    private void uploadImage(File imageFile) {
        OkHttpClient client = new OkHttpClient();

        RequestBody requestBody = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", imageFile.getName(),
                        RequestBody.create(MediaType.parse("image/jpeg"), imageFile))
                .build();

        Request request = new Request.Builder()
                .url("https://wallet-agent-203063692416.asia-south1.run.app/upload-image")
                .post(requestBody)
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(@NonNull Call call, @NonNull IOException e) {
                Log.e(TAG, "Image upload failed: " + e.getMessage(), e);
                runOnUiThread(() -> Toast.makeText(CameraActivity.this, "Upload failed: " + e.getMessage(), Toast.LENGTH_LONG).show());
            }

            @Override
            public void onResponse(@NonNull Call call, @NonNull Response response) throws IOException {
                if (response.isSuccessful()) {
                    String responseBody = response.body() != null ? response.body().string() : "Empty response";
                    Log.d(TAG, "Image upload successful: " + responseBody);
                    runOnUiThread(() -> {
                        Toast.makeText(CameraActivity.this, "Upload successful", Toast.LENGTH_SHORT).show();
                        try {
                            Gson gson = new Gson();
                            // Assuming the top-level structure is a map with "ocr_result" and "receipt_id"
                            Map<String, Object> apiResponse = gson.fromJson(responseBody, Map.class);
                            Map<String, Object> ocrResultMap = (Map<String, Object>) apiResponse.get("ocr_result");

                            // Convert the ocr_result map back to JSON string to parse it into OcrData object
                            String ocrResultJson = gson.toJson(ocrResultMap);
                            OcrData ocrData = gson.fromJson(ocrResultJson, OcrData.class);

                            Log.d(TAG, "Parsed OCR Data: " + ocrData.toString());

                            Intent intent = new Intent(CameraActivity.this, ReceiptReviewActivity.class);
                            intent.putExtra("ocrData", ocrData);
                            startActivity(intent);
                            finish(); // Finish CameraActivity after navigating
                        } catch (JsonSyntaxException e) {
                            Log.e(TAG, "Error parsing JSON response: " + e.getMessage(), e);
                            Toast.makeText(CameraActivity.this, "Error processing OCR data", Toast.LENGTH_LONG).show();
                        }
                    });
                } else {
                    runOnUiThread(() -> Toast.makeText(CameraActivity.this, "Upload failed: " + response.code(), Toast.LENGTH_LONG).show());
                }
                // Clean up the temporary file after upload attempt
                if (imageFile.exists()) {
                    imageFile.delete();
                }
            }
        });
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        cameraExecutor.shutdown();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode,
                                           @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == PERMISSION_REQUEST_CODE) {
            if (allPermissionsGranted()) {
                startCamera();
            } else {
                Toast.makeText(this, "Camera permission required", Toast.LENGTH_SHORT).show();
                finish();
            }
        }
    }
}
