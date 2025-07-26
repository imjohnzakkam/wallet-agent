package com.example.raseed;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.view.View;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import com.google.gson.Gson;

import java.io.IOException;
import java.io.InputStream;
import java.util.concurrent.TimeUnit;
import java.io.ByteArrayOutputStream;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public class ShareIntentActivity extends AppCompatActivity {

    private View loadingOverlay;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_share_receiver);

        loadingOverlay = findViewById(R.id.loading_overlay);
        Log.i("ShareIntentActivity", "Request received to onCreate");

        Intent intent = getIntent();
        if (Intent.ACTION_SEND.equals(intent.getAction()) && intent.getType() != null) {
            if (intent.getType().startsWith("image/")) {
                Uri imageUri = intent.getParcelableExtra(Intent.EXTRA_STREAM);
                if (imageUri != null) {
                    uploadImageToOCR(imageUri);
                } else {
                    Toast.makeText(this, "No image found", Toast.LENGTH_SHORT).show();
                    finish();
                }
            } else {
                Toast.makeText(this, "Unsupported type", Toast.LENGTH_SHORT).show();
                finish();
            }
        } else {
            finish();
        }
    }

    private void uploadImageToOCR(Uri imageUri) {
        Log.i("ShareIntentActivity", "Request received to uploadImageToOCR");
        showLoading(true);

        try (InputStream inputStream = getContentResolver().openInputStream(imageUri)) {
            byte[] imageBytes = readBytes(inputStream);

            // Get the correct MIME type for the image (e.g., image/jpeg or image/png)
            String mimeType = getContentResolver().getType(imageUri);
            if (mimeType == null) mimeType = "image/jpeg"; // fallback if not found

            RequestBody imageBody = RequestBody.create(imageBytes, MediaType.parse(mimeType));

            // Multipart form with correct part name and MIME
            RequestBody requestBody = new MultipartBody.Builder()
                    .setType(MultipartBody.FORM)
                    .addFormDataPart("file", "receipt.jpg", imageBody)
                    .build();

            OkHttpClient client = new OkHttpClient.Builder()
                    .connectTimeout(30, TimeUnit.SECONDS)
                    .readTimeout(30, TimeUnit.SECONDS)
                    .writeTimeout(30, TimeUnit.SECONDS)
                    .build();

            Request request = new Request.Builder()
                    .url("https://wallet-agent-203063692416.asia-south1.run.app/upload-image")
                    .post(requestBody)
                    .build();

            client.newCall(request).enqueue(new Callback() {
                @Override
                public void onFailure(Call call, IOException e) {
                    runOnUiThread(() -> {
                        Log.e("ShareIntentActivity", "Failure from API call");
                        showLoading(false);
                        Toast.makeText(ShareIntentActivity.this, "OCR Failed", Toast.LENGTH_SHORT).show();
                        finish();
                    });
                }

                @Override
                public void onResponse(Call call, Response response) throws IOException {
                    runOnUiThread(() -> showLoading(false));

                    if (response.isSuccessful()) {
                        try {
                            String responseBody = response.body().string();
                            Gson gson = new Gson();
                            OcrResponse ocrResponse = gson.fromJson(responseBody, OcrResponse.class);

                            Intent reviewIntent = new Intent(ShareIntentActivity.this, ReceiptReviewActivity.class);
                            reviewIntent.putExtra("vendor", ocrResponse.ocrResult.vendorName);
                            reviewIntent.putExtra("category", ocrResponse.ocrResult.category);
                            reviewIntent.putExtra("date", ocrResponse.ocrResult.dateTime.split("T")[0]);
                            reviewIntent.putExtra("time", ocrResponse.ocrResult.dateTime.split("T")[1]);
                            reviewIntent.putExtra("amount", String.valueOf(ocrResponse.ocrResult.amount));
                            reviewIntent.putExtra("receipt_id", ocrResponse.receiptId);
                            reviewIntent.putExtra("imagePath", imageUri.toString());

                            startActivity(reviewIntent);
                            finish();
                        } catch (Exception e) {
                            runOnUiThread(() -> {
                                Log.e("ShareIntentActivity", "Failure from review intent flow");
                                Toast.makeText(ShareIntentActivity.this, "Parsing Error", Toast.LENGTH_SHORT).show();
                                finish();
                            });
                        }
                    } else {
                        runOnUiThread(() -> {
                            Toast.makeText(ShareIntentActivity.this, "Server Error " + response.code(), Toast.LENGTH_SHORT).show();
                            finish();
                        });
                    }
                }
            });

        } catch (Exception e) {
            showLoading(false);
            Toast.makeText(this, "Error reading image", Toast.LENGTH_SHORT).show();
            finish();
        }
    }

    private void showLoading(boolean show) {
        if (loadingOverlay != null) {
            loadingOverlay.setVisibility(show ? View.VISIBLE : View.GONE);
        }
    }

    private byte[] readBytes(InputStream inputStream) throws IOException {
        ByteArrayOutputStream byteBuffer = new ByteArrayOutputStream();
        byte[] buffer = new byte[1024];
        int len;
        while ((len = inputStream.read(buffer)) != -1) {
            byteBuffer.write(buffer, 0, len);
        }
        return byteBuffer.toByteArray();
    }
}

