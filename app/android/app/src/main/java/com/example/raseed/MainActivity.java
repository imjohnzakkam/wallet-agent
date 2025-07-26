package com.example.raseed;

import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.util.Log;
import android.view.Menu;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.RelativeLayout;
import android.widget.Toast;

import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.google.gson.Gson;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.ArrayList;
import java.util.BitSet;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.util.List;
import java.util.concurrent.TimeUnit;

import okhttp3.Call;
import okhttp3.Callback;
import okhttp3.MediaType;
import okhttp3.MultipartBody;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.RequestBody;
import okhttp3.Response;

public class MainActivity extends AppCompatActivity {

    private EditText inputMessage;
    private Button sendButton;
    private RecyclerView chatRecyclerView;
    private ChatAdapter chatAdapter;
    private List<ChatMessage> chatMessages;
    private RelativeLayout loadingOverlay;


    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        inputMessage = findViewById(R.id.messageInput);
        sendButton = findViewById(R.id.sendButton);
        chatRecyclerView = findViewById(R.id.chatRecyclerView);
        loadingOverlay = findViewById(R.id.loadingOverlay);

        chatMessages = new ArrayList<>();
        chatAdapter = new ChatAdapter(chatMessages);
        chatRecyclerView.setLayoutManager(new LinearLayoutManager(this));
        chatRecyclerView.setAdapter(chatAdapter);

        sendButton.setOnClickListener(v -> {
            String userMessage = inputMessage.getText().toString().trim();
            if (!userMessage.isEmpty()) {
                chatMessages.add(new ChatMessage(userMessage, true));
                chatAdapter.notifyItemInserted(chatMessages.size() - 1);
                inputMessage.setText("");
                sendToBackend(userMessage);
            }
        });

        Toolbar toolbar = findViewById(R.id.chatToolbar);
        setSupportActionBar(toolbar);

        toolbar.setOnMenuItemClickListener(item -> {
            if (item.getItemId() == R.id.capture_receipt) {
                // Launch CameraActivity
                Intent intent = new Intent(MainActivity.this, CameraActivity.class);
                startActivity(intent);
                return true;
            }
            else if (item.getItemId() == R.id.upload_receipt) {
                // Handle file picker
                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.setType("image/*");
                startActivityForResult(Intent.createChooser(intent, "Select Picture"), 101);
                return true;
            }
            return false;
        });
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        getMenuInflater().inflate(R.menu.chat_menu, menu);
        return true;
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, @Nullable Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == 101 && resultCode == RESULT_OK && data != null) {
            Uri selectedImageUri = data.getData();

            if (selectedImageUri != null) {
                showLoading(true);
                // Send this image URI to your OCR API
                uploadImageToOCR(selectedImageUri);
            }
        }
    }

    private void uploadImageToOCR(Uri imageUri) {
        showLoading(true); // Start loading as early as possible

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

            Log.i("MainActivity", "uploadImageToOCR :: requestBody formed");

            client.newCall(request).enqueue(new Callback() {
                @Override
                public void onFailure(Call call, IOException e) {
                    runOnUiThread(() -> {
                        showLoading(false);
                        Log.e("MainActivity", "uploadImageToOCR :: onFailure", e);
                        Toast.makeText(MainActivity.this, "OCR Failed: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                    });
                }

                @Override
                public void onResponse(Call call, Response response) throws IOException {
                    runOnUiThread(() -> showLoading(false)); // Hide loading no matter what

                    if (response.isSuccessful()) {
                        try {
                            String responseBody = response.body().string();
                            Gson gson = new Gson();
                            OcrResponse ocrResponse = gson.fromJson(responseBody, OcrResponse.class);
                            Log.i("MainActivity", "uploadImageToOCR :: responseBody parsed");

                            Intent reviewIntent = new Intent(MainActivity.this, ReceiptReviewActivity.class);
                            reviewIntent.putExtra("vendor", ocrResponse.ocrResult.vendorName);
                            reviewIntent.putExtra("category", ocrResponse.ocrResult.category);
                            reviewIntent.putExtra("date", ocrResponse.ocrResult.dateTime.split("T")[0]);
                            reviewIntent.putExtra("time", ocrResponse.ocrResult.dateTime.split("T")[1]);
                            reviewIntent.putExtra("amount", String.valueOf(ocrResponse.ocrResult.amount));
                            reviewIntent.putExtra("receipt_id", ocrResponse.receiptId);
                            reviewIntent.putExtra("imagePath", imageUri.toString());

                            runOnUiThread(() -> startActivity(reviewIntent));
                        } catch (Exception e) {
                            runOnUiThread(() -> {
                                Toast.makeText(MainActivity.this, "Error parsing OCR result", Toast.LENGTH_SHORT).show();
                                Log.e("MainActivity", "uploadImageToOCR :: parsing failed", e);
                            });
                        }
                    } else {
                        runOnUiThread(() -> {
                            Toast.makeText(MainActivity.this, "Server Error: " + response.code(), Toast.LENGTH_SHORT).show();
                            Log.e("MainActivity", "uploadImageToOCR :: server error " + response.code());
                        });
                    }
                }
            });

        } catch (Exception e) {
            e.printStackTrace();
            showLoading(false);
            Toast.makeText(this, "Error reading image", Toast.LENGTH_SHORT).show();
        }
    }

    private byte[] readBytes(InputStream inputStream) throws IOException {
        ByteArrayOutputStream byteBuffer = new ByteArrayOutputStream();
        int bufferSize = 1024;
        byte[] buffer = new byte[bufferSize];

        int len;
        while ((len = inputStream.read(buffer)) != -1) {
            byteBuffer.write(buffer, 0, len);
        }
        return byteBuffer.toByteArray();
    }



    private void showLoading(boolean show) {
        if (loadingOverlay != null) {
            loadingOverlay.setVisibility(show ? View.VISIBLE : View.GONE);
        }
    }

    private void sendToBackend(String message) {
        // Replace with your real backend API
        new Thread(() -> {
            try {
                URL url = new URL("https://your-backend.com/api/chat");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);

                JSONObject json = new JSONObject();
                json.put("query", message);

                OutputStream os = conn.getOutputStream();
                os.write(json.toString().getBytes());
                os.close();

                BufferedReader in = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = in.readLine()) != null) {
                    response.append(line);
                }
                in.close();

                String reply = response.toString();
                runOnUiThread(() -> {
                    chatMessages.add(new ChatMessage(reply, false));
                    chatAdapter.notifyItemInserted(chatMessages.size() - 1);
                    chatRecyclerView.smoothScrollToPosition(chatMessages.size() - 1);
                });

            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }
}

