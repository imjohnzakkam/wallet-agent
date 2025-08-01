package com.example.raseed;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Button;
import android.widget.ProgressBar;
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
import com.google.gson.annotations.SerializedName;

import java.io.File;
import java.io.IOException;
import java.io.Serializable;
import java.text.SimpleDateFormat;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.Executors;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

// Top-level response
class OcrResponse implements Serializable {
    @SerializedName("receipt_data")
    public OcrResult ocrResult;

    @SerializedName("receipt_id")
    public String receiptId;

    public static class OcrResult implements Serializable {
        @SerializedName("vendor_name")
        public String vendorName;

        @SerializedName("category")
        public String category;

        @SerializedName("date_time")
        public String dateTime;

        @SerializedName("amount")
        public double amount;

        @SerializedName("subtotal")
        public double subtotal;

        @SerializedName("tax")
        public double tax;

        @SerializedName("currency")
        public String currency;

        @SerializedName("payment_method")
        public String paymentMethod;

        @SerializedName("language")
        public String language;

        @SerializedName("items")
        public List<OcrItem> items;
    }

    public static class OcrItem implements Serializable {
        @SerializedName("name")
        public String name;

        @SerializedName("quantity")
        public double quantity;

        @SerializedName("unit")
        public String unit;

        @SerializedName("price")
        public double price;

        @SerializedName("category")
        public String category;
    }
}

public class CameraActivity extends AppCompatActivity {

    private static final int PERMISSION_REQUEST_CODE = 1001;
    private static final String TAG = "CameraActivity";

    private PreviewView previewView;
    private ImageCapture imageCapture;
    private ExecutorService cameraExecutor;
    private ProgressBar progressBar;


    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_camera);

        progressBar = findViewById(R.id.progressBar);
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
                    }

                    @Override
                    public void onError(@NonNull ImageCaptureException exception) {
                        Log.e(TAG, "Photo capture failed: " + exception.getMessage(), exception);
                        runOnUiThread(() -> Toast.makeText(CameraActivity.this, "Capture failed", Toast.LENGTH_SHORT).show());
                    }
                });
    }
    private void uploadImage(File imageFile) {
        Log.i(TAG, "uploadImage :: request received");
        runOnUiThread(() -> progressBar.setVisibility(View.VISIBLE));

        OkHttpClient client = new OkHttpClient.Builder()
                .connectTimeout(30, TimeUnit.SECONDS) // Connection timeout
                .readTimeout(30, TimeUnit.SECONDS)    // Read timeout
                .writeTimeout(30, TimeUnit.SECONDS)   // Write timeout
                .build();

        RequestBody requestBody = new MultipartBody.Builder()
                .setType(MultipartBody.FORM)
                .addFormDataPart("file", imageFile.getName(),
                        RequestBody.create(MediaType.parse("image/jpeg"), imageFile))
                .build();

        Request request = new Request.Builder()
                .url("https://wallet-agent-203063692416.asia-south1.run.app/upload-image")
                .post(requestBody)
                .build();

        Log.i(TAG, "uploadImage :: requestBody formed");

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(@NonNull Call call, @NonNull IOException e) {
                runOnUiThread(() -> {
                    Log.i(TAG, "uploadImage :: request failed " + e.getMessage());
                    progressBar.setVisibility(View.GONE);
                    Toast.makeText(CameraActivity.this, "Upload failed: " + e.getMessage(), Toast.LENGTH_LONG).show();
                });
            }

            @Override
            public void onResponse(@NonNull Call call, @NonNull Response response) throws IOException {
                String responseBodyStr = response.body() != null ? response.body().string() : "Empty response";

                if (response.isSuccessful()) {
                    Log.i(TAG, "Image upload successful: " + responseBodyStr);
                    try {
                        Gson gson = new Gson();
                        OcrResponse ocrResponse = gson.fromJson(responseBodyStr, OcrResponse.class);

                        if (ocrResponse == null || ocrResponse.ocrResult == null) {
                            runOnUiThread(() -> {
                                progressBar.setVisibility(View.GONE);
                                Toast.makeText(CameraActivity.this, "OCR result missing in response", Toast.LENGTH_LONG).show();
                            });
                            return;
                        }

                        runOnUiThread(() -> {
                            progressBar.setVisibility(View.GONE);
                            Intent reviewIntent = new Intent(CameraActivity.this, ReceiptReviewActivity.class);
                            reviewIntent.putExtra("vendor", ocrResponse.ocrResult.vendorName);
                            reviewIntent.putExtra("category", ocrResponse.ocrResult.category);
                            reviewIntent.putExtra("date", ocrResponse.ocrResult.dateTime.split("T")[0]);
                            reviewIntent.putExtra("time", ocrResponse.ocrResult.dateTime.split("T")[1]);
                            reviewIntent.putExtra("amount", String.valueOf(ocrResponse.ocrResult.amount));
                            reviewIntent.putExtra("receipt_id", ocrResponse.receiptId);
                            reviewIntent.putExtra("user_id", "123");
                            Uri imageUri = Uri.fromFile(imageFile);
                            reviewIntent.putExtra("imagePath", imageUri.toString());

                            startActivity(reviewIntent);
                            finish();
                        });

                    } catch (JsonSyntaxException e) {
                        Log.e(TAG, "Error parsing JSON response: " + e.getMessage(), e);
                        runOnUiThread(() -> {
                            progressBar.setVisibility(View.GONE);
                            Toast.makeText(CameraActivity.this, "Error processing OCR data", Toast.LENGTH_LONG).show();
                        });
                    }
                } else {
                    runOnUiThread(() -> {
                        progressBar.setVisibility(View.GONE);
                        Toast.makeText(CameraActivity.this, "Upload failed: " + response.code(), Toast.LENGTH_LONG).show();
                    });
                }

                // Cleanup temp image file
//                if (imageFile.exists()) {
//                    imageFile.delete();
//                }
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
