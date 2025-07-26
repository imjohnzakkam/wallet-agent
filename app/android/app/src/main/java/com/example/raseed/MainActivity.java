package com.example.raseed;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioRecord;
import android.media.AudioTrack;
import android.media.MediaRecorder;
import android.net.Uri;
import android.os.Bundle;
import android.util.Base64;
import android.util.Log;
import android.view.ContextMenu;
import android.view.Menu;
import android.view.MenuItem;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.ProgressBar;
import android.widget.RelativeLayout;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.annotation.Nullable;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.google.gson.Gson;
import com.google.gson.JsonObject;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.ArrayList;
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

public class MainActivity extends AppCompatActivity implements ChatAdapter.OnMessageLongClickListener {

    private EditText inputMessage;
    private Button sendButton;
    private RecyclerView chatRecyclerView;
    private ChatAdapter chatAdapter;
    private List<ChatMessage> chatMessages;
    private RelativeLayout loadingOverlay;

    // Voice related variables
    private ImageButton voiceButton;
    private ProgressBar loadingSpinner;
    private boolean isRecording = false;
    private AudioRecord recorder;
    private Thread recordingThread;
    private static final int RECORD_AUDIO_REQUEST_CODE = 1;

    // Audio recording settings
    private static final int SAMPLE_RATE = 16000;
    private static final int CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO;
    private static final int AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT;
    private int bufferSize;
    private ByteArrayOutputStream audioDataStream;

    // GCP API settings
    private static final String GCP_API_KEY = "AIzaSyB_F8_C6WHzuZgz8ugUnFatDTwak8sSFGs"; // Replace with your actual API key
    private static final String SPEECH_TO_TEXT_URL = "https://speech.googleapis.com/v1/speech:recognize?key=" + GCP_API_KEY;
    private static final String TEXT_TO_SPEECH_URL = "https://texttospeech.googleapis.com/v1/text:synthesize?key=" + GCP_API_KEY;

    // Audio playback
    private AudioTrack audioTrack;
    private boolean isPlaying = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        inputMessage = findViewById(R.id.messageInput);
        sendButton = findViewById(R.id.sendButton);
        chatRecyclerView = findViewById(R.id.chatRecyclerView);
        loadingOverlay = findViewById(R.id.loadingOverlay);
        voiceButton = findViewById(R.id.voiceButton);

        chatMessages = new ArrayList<>();
        chatAdapter = new ChatAdapter(chatMessages, this); // Pass listener to adapter
        chatRecyclerView.setLayoutManager(new LinearLayoutManager(this));
        chatRecyclerView.setAdapter(chatAdapter);

        // Calculate buffer size for audio recording
        bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT);

        sendButton.setOnClickListener(v -> {
            String userMessage = inputMessage.getText().toString().trim();
            if (!userMessage.isEmpty()) {
                chatMessages.add(new ChatMessage(userMessage, true));
                chatAdapter.notifyItemInserted(chatMessages.size() - 1);
                inputMessage.setText("");
                sendToBackend(userMessage);
            }
        });

        // Voice button click listener
        voiceButton.setOnClickListener(v -> {
            if (isRecording) {
                stopRecording();
            } else {
                startRecording();
            }
        });

        Toolbar toolbar = findViewById(R.id.chatToolbar);
        setSupportActionBar(toolbar);

        toolbar.setOnMenuItemClickListener(item -> {
            if (item.getItemId() == R.id.capture_receipt) {
                Intent intent = new Intent(MainActivity.this, CameraActivity.class);
                startActivity(intent);
                return true;
            }
            else if (item.getItemId() == R.id.upload_receipt) {
                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.setType("image/*");
                startActivityForResult(Intent.createChooser(intent, "Select Picture"), 101);
                return true;
            }
            return false;
        });

        // Check for audio recording permission
        checkAudioPermission();
    }

    // Interface implementation for long click listener
    @Override
    public void onMessageLongClick(ChatMessage message, View view) {
        if (!message.isUser()) { // Only allow TTS for received messages
            showPopupMenu(message, view);
        } else {
            Log.d("MainActivity", "Ignoring long click on user message");
        }
    }

    private void showPopupMenu(ChatMessage message, View view) {
        androidx.appcompat.widget.PopupMenu popup = new androidx.appcompat.widget.PopupMenu(this, view);
        popup.getMenuInflater().inflate(R.menu.message_popup_menu, popup.getMenu());

        popup.setOnMenuItemClickListener(item -> {
            if (item.getItemId() == R.id.listen_to_message) {
                convertTextToSpeech(message.getText());
                return true;
            }
            return false;
        });

        popup.show();
    }

    private void convertTextToSpeech(String text) {
        if (isPlaying) {
            Toast.makeText(this, "Already playing audio", Toast.LENGTH_SHORT).show();
            Log.d("MainActivity", "Already playing audio, returning");
            return;
        }

        showLoading(true);
        Toast.makeText(this, "Converting message to audio...", Toast.LENGTH_LONG).show();

        new Thread(() -> {
            try {

                // Create JSON request for GCP Text-to-Speech API
                JSONObject input = new JSONObject();
                input.put("text", text);

                JSONObject voice = new JSONObject();
                voice.put("languageCode", "en-US");
                voice.put("name", "en-US-Neural2-F"); // Female voice, you can change this
                voice.put("ssmlGender", "FEMALE");

                JSONObject audioConfig = new JSONObject();
                audioConfig.put("audioEncoding", "LINEAR16");
                audioConfig.put("sampleRateHertz", 22050);

                JSONObject request = new JSONObject();
                request.put("input", input);
                request.put("voice", voice);
                request.put("audioConfig", audioConfig);

                // Make API call
                OkHttpClient client = new OkHttpClient.Builder()
                        .connectTimeout(30, TimeUnit.SECONDS)
                        .readTimeout(30, TimeUnit.SECONDS)
                        .writeTimeout(30, TimeUnit.SECONDS)
                        .build();

                RequestBody body = RequestBody.create(
                        request.toString(),
                        MediaType.parse("application/json; charset=utf-8")
                );

                Request apiRequest = new Request.Builder()
                        .url(TEXT_TO_SPEECH_URL)
                        .post(body)
                        .build();

                client.newCall(apiRequest).enqueue(new Callback() {
                    @Override
                    public void onFailure(Call call, IOException e) {
                        Log.e("MainActivity", "TTS API call failed", e);
                        runOnUiThread(() -> {
                            showLoading(false);
                            Toast.makeText(MainActivity.this,
                                    "Text-to-speech failed: " + e.getMessage(),
                                    Toast.LENGTH_LONG).show();
                            Log.e("MainActivity", "TTS API failed", e);
                        });
                    }

                    @Override
                    public void onResponse(Call call, Response response) throws IOException {
                        Log.d("MainActivity", "TTS API response received. Code: " + response.code());
                        runOnUiThread(() -> showLoading(false));

                        if (response.isSuccessful()) {
                            try {
                                String responseBody = response.body().string();
                                Log.d("MainActivity", "TTS API response body length: " + responseBody.length());

                                JSONObject jsonResponse = new JSONObject(responseBody);

                                if (jsonResponse.has("audioContent")) {
                                    String audioContent = jsonResponse.getString("audioContent");
                                    Log.d("MainActivity", "Audio content received, length: " + audioContent.length());
                                    byte[] audioData = Base64.decode(audioContent, Base64.DEFAULT);
                                    Log.d("MainActivity", "Decoded audio data size: " + audioData.length + " bytes");

                                    runOnUiThread(() -> {
                                        Toast.makeText(MainActivity.this,
                                                "Playing audio...", Toast.LENGTH_SHORT).show();
                                        playAudio(audioData);
                                    });
                                } else {
                                    Log.e("MainActivity", "No audioContent in response: " + responseBody);
                                    runOnUiThread(() -> {
                                        Toast.makeText(MainActivity.this,
                                                "No audio content received", Toast.LENGTH_SHORT).show();
                                    });
                                }

                            } catch (JSONException e) {
                                Log.e("MainActivity", "TTS JSON parsing error", e);
                                runOnUiThread(() -> {
                                    Toast.makeText(MainActivity.this,
                                            "Error parsing TTS response", Toast.LENGTH_SHORT).show();
                                });
                            }
                        } else {
                            String errorBody = "";
                            try {
                                errorBody = response.body().string();
                            } catch (IOException e) {
                                Log.e("MainActivity", "Error reading error response", e);
                            }
                            Log.e("MainActivity", "TTS API error: " + response.code() + " - " + errorBody);
                            runOnUiThread(() -> {
                                Toast.makeText(MainActivity.this,
                                        "TTS API error: " + response.code(), Toast.LENGTH_LONG).show();
                            });
                        }
                    }
                });

            } catch (Exception e) {
                Log.e("MainActivity", "Error in convertTextToSpeech", e);
                runOnUiThread(() -> {
                    showLoading(false);
                    Toast.makeText(MainActivity.this,
                            "Error processing TTS: " + e.getMessage(), Toast.LENGTH_LONG).show();
                });
            }
        }).start();
    }

    private void playAudio(byte[] audioData) {
        Log.d("MainActivity", "playAudio called with " + audioData.length + " bytes");

        new Thread(() -> {
            try {
                isPlaying = true;
                Log.d("MainActivity", "Starting audio playback...");

                int sampleRate = 22050;
                int minBufferSize = AudioTrack.getMinBufferSize(
                        sampleRate,
                        AudioFormat.CHANNEL_OUT_MONO,
                        AudioFormat.ENCODING_PCM_16BIT
                );

                Log.d("MainActivity", "Audio track buffer size: " + minBufferSize);

                audioTrack = new AudioTrack(
                        AudioManager.STREAM_MUSIC,
                        sampleRate,
                        AudioFormat.CHANNEL_OUT_MONO,
                        AudioFormat.ENCODING_PCM_16BIT,
                        minBufferSize,
                        AudioTrack.MODE_STREAM
                );

                Log.d("MainActivity", "AudioTrack created, starting playback");
                audioTrack.play();

                int bytesWritten = audioTrack.write(audioData, 0, audioData.length);
                Log.d("MainActivity", "Bytes written to audio track: " + bytesWritten);

                audioTrack.stop();
                audioTrack.release();

                isPlaying = false;
                Log.d("MainActivity", "Audio playback completed");

                runOnUiThread(() -> {
                    Toast.makeText(MainActivity.this, "Audio playback finished", Toast.LENGTH_SHORT).show();
                });

            } catch (Exception e) {
                isPlaying = false;
                Log.e("MainActivity", "Error playing audio", e);
                runOnUiThread(() -> {
                    Toast.makeText(MainActivity.this, "Error playing audio: " + e.getMessage(), Toast.LENGTH_LONG).show();
                });
            }
        }).start();
    }

    private void checkAudioPermission() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.RECORD_AUDIO},
                    RECORD_AUDIO_REQUEST_CODE);
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == RECORD_AUDIO_REQUEST_CODE) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                Toast.makeText(this, "Audio permission granted", Toast.LENGTH_SHORT).show();
            } else {
                Toast.makeText(this, "Audio permission denied", Toast.LENGTH_SHORT).show();
                voiceButton.setEnabled(false);
            }
        }
    }

    private void startRecording() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            Toast.makeText(this, "Audio permission required", Toast.LENGTH_SHORT).show();
            return;
        }

        try {
            recorder = new AudioRecord(MediaRecorder.AudioSource.MIC,
                    SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT, bufferSize);

            if (recorder.getState() != AudioRecord.STATE_INITIALIZED) {
                Toast.makeText(this, "Failed to initialize audio recorder", Toast.LENGTH_SHORT).show();
                return;
            }

            audioDataStream = new ByteArrayOutputStream();
            isRecording = true;

            // Update UI
            voiceButton.setImageResource(R.drawable.stop_button); // You'll need a stop icon
            Toast.makeText(this, "Recording started...", Toast.LENGTH_SHORT).show();

            recorder.startRecording();

            recordingThread = new Thread(this::recordAudio);
            recordingThread.start();

        } catch (Exception e) {
            Log.e("MainActivity", "Error starting recording", e);
            Toast.makeText(this, "Failed to start recording", Toast.LENGTH_SHORT).show();
        }
    }

    private void recordAudio() {
        byte[] audioBuffer = new byte[bufferSize];

        while (isRecording && recorder != null) {
            int bytesRead = recorder.read(audioBuffer, 0, bufferSize);
            if (bytesRead > 0) {
                audioDataStream.write(audioBuffer, 0, bytesRead);
            }
        }
    }

    private void stopRecording() {
        if (!isRecording) return;

        isRecording = false;

        if (recorder != null) {
            try {
                recorder.stop();
                recorder.release();
                recorder = null;
            } catch (Exception e) {
                Log.e("MainActivity", "Error stopping recording", e);
            }
        }

        if (recordingThread != null) {
            try {
                recordingThread.join();
            } catch (InterruptedException e) {
                Log.e("MainActivity", "Recording thread interrupted", e);
            }
        }

        // Update UI
        voiceButton.setImageResource(R.drawable.microphone); // Your mic icon
        Toast.makeText(this, "Recording stopped. Processing...", Toast.LENGTH_SHORT).show();

        // Process the recorded audio
        if (audioDataStream != null && audioDataStream.size() > 0) {
            byte[] audioData = audioDataStream.toByteArray();
            sendAudioToSpeechAPI(audioData);
        } else {
            Toast.makeText(this, "No audio recorded", Toast.LENGTH_SHORT).show();
        }
    }

    private void sendAudioToSpeechAPI(byte[] audioData) {
        showLoading(true);

        new Thread(() -> {
            try {
                // Convert audio data to base64
                String audioBase64 = Base64.encodeToString(audioData, Base64.NO_WRAP);

                // Create JSON request for GCP Speech-to-Text API
                JSONObject config = new JSONObject();
                config.put("encoding", "LINEAR16");
                config.put("sampleRateHertz", SAMPLE_RATE);
                config.put("languageCode", "en-US"); // Change to your preferred language
                config.put("enableAutomaticPunctuation", true);

                JSONObject audio = new JSONObject();
                audio.put("content", audioBase64);

                JSONObject request = new JSONObject();
                request.put("config", config);
                request.put("audio", audio);

                // Make API call
                OkHttpClient client = new OkHttpClient.Builder()
                        .connectTimeout(30, TimeUnit.SECONDS)
                        .readTimeout(30, TimeUnit.SECONDS)
                        .writeTimeout(30, TimeUnit.SECONDS)
                        .build();

                RequestBody body = RequestBody.create(
                        request.toString(),
                        MediaType.parse("application/json; charset=utf-8")
                );

                Request apiRequest = new Request.Builder()
                        .url(SPEECH_TO_TEXT_URL)
                        .post(body)
                        .build();

                client.newCall(apiRequest).enqueue(new Callback() {
                    @Override
                    public void onFailure(Call call, IOException e) {
                        runOnUiThread(() -> {
                            showLoading(false);
                            Toast.makeText(MainActivity.this,
                                    "Speech recognition failed: " + e.getMessage(),
                                    Toast.LENGTH_SHORT).show();
                            Log.e("MainActivity", "Speech API failed", e);
                        });
                    }

                    @Override
                    public void onResponse(Call call, Response response) throws IOException {
                        runOnUiThread(() -> showLoading(false));

                        if (response.isSuccessful()) {
                            try {
                                String responseBody = response.body().string();
                                Log.d("MainActivity", "Speech API response: " + responseBody);

                                JSONObject jsonResponse = new JSONObject(responseBody);

                                if (jsonResponse.has("results") &&
                                        jsonResponse.getJSONArray("results").length() > 0) {

                                    String transcript = jsonResponse
                                            .getJSONArray("results")
                                            .getJSONObject(0)
                                            .getJSONArray("alternatives")
                                            .getJSONObject(0)
                                            .getString("transcript");

                                    runOnUiThread(() -> {
                                        // Add the transcribed message to chat
                                        chatMessages.add(new ChatMessage(transcript, true));
                                        chatAdapter.notifyItemInserted(chatMessages.size() - 1);
                                        chatRecyclerView.smoothScrollToPosition(chatMessages.size() - 1);

                                        // Send to backend
                                        sendToBackend(transcript);

                                        Toast.makeText(MainActivity.this,
                                                "Voice message sent: " + transcript,
                                                Toast.LENGTH_SHORT).show();
                                    });
                                } else {
                                    runOnUiThread(() -> {
                                        Toast.makeText(MainActivity.this,
                                                "No speech detected",
                                                Toast.LENGTH_SHORT).show();
                                    });
                                }

                            } catch (JSONException e) {
                                runOnUiThread(() -> {
                                    Toast.makeText(MainActivity.this,
                                            "Error parsing speech response",
                                            Toast.LENGTH_SHORT).show();
                                    Log.e("MainActivity", "JSON parsing error", e);
                                });
                            }
                        } else {
                            runOnUiThread(() -> {
                                Toast.makeText(MainActivity.this,
                                        "Speech API error: " + response.code(),
                                        Toast.LENGTH_SHORT).show();
                                Log.e("MainActivity", "Speech API error: " + response.code());
                            });
                        }
                    }
                });

            } catch (Exception e) {
                runOnUiThread(() -> {
                    showLoading(false);
                    Toast.makeText(MainActivity.this,
                            "Error processing audio: " + e.getMessage(),
                            Toast.LENGTH_SHORT).show();
                    Log.e("MainActivity", "Error processing audio", e);
                });
            }
        }).start();
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
                uploadImageToOCR(selectedImageUri);
            }
        }
    }

    private void uploadImageToOCR(Uri imageUri) {
        showLoading(true);

        try (InputStream inputStream = getContentResolver().openInputStream(imageUri)) {
            byte[] imageBytes = readBytes(inputStream);

            String mimeType = getContentResolver().getType(imageUri);
            if (mimeType == null) mimeType = "image/jpeg";

            RequestBody imageBody = RequestBody.create(imageBytes, MediaType.parse(mimeType));

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
                    runOnUiThread(() -> showLoading(false));

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
        new Thread(() -> {
            try {
                Thread.sleep(1000);

                String llmResponse;
                String walletLink;

                if (message.toLowerCase().contains("receipt")) {
                    llmResponse = "Here are your recent grocery receipts from Big Bazaar and Reliance Fresh.";
                    walletLink = "https://pay.google.com/gp/v/save/receipt-pass-id";
                } else {
                    llmResponse = "You spent ₹2,340 on groceries last week, mainly at Big Bazaar and FreshMart.";
                    walletLink = "";
                }

                runOnUiThread(() -> {
                    chatMessages.add(new ChatMessage(llmResponse, false, walletLink));
                    chatAdapter.notifyItemInserted(chatMessages.size() - 1);
                    chatRecyclerView.smoothScrollToPosition(chatMessages.size() - 1);
                });

            } catch (Exception e) {
                e.printStackTrace();
                runOnUiThread(() -> {
                    chatMessages.add(new ChatMessage("Error: " + e.getMessage(), false));
                    chatAdapter.notifyItemInserted(chatMessages.size() - 1);
                });
            }
        }).start();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (isRecording) {
            stopRecording();
        }
        if (audioTrack != null) {
            audioTrack.release();
        }
    }
}