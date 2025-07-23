package com.example.raseed;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.util.Log;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import okhttp3.*;

import java.io.IOException;

public class AskActivity extends AppCompatActivity {

    // TODO : Replace with the correct endpoint
    private static final String API_URL = "https://your-api.com/ask"; // Replace with real endpoint
    private EditText questionInput;
    private Button submitBtn;
    private TextView responseView;

    private final OkHttpClient client = new OkHttpClient();
    private final Handler mainHandler = new Handler(Looper.getMainLooper()); // To update UI from background thread

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_ask);

        questionInput = findViewById(R.id.questionInput);
        submitBtn = findViewById(R.id.submitQuestionBtn);
        responseView = findViewById(R.id.responseView);

        submitBtn.setOnClickListener(v -> {
            String question = questionInput.getText().toString().trim();
            if (!question.isEmpty()) {
                responseView.setText("Sending...");
                sendQuestionToApi(question);
            } else {
                Toast.makeText(this, "Please enter a question", Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void sendQuestionToApi(String question) {
        // TODO : Build the correct application/json request body with the correct parameters
        RequestBody requestBody = new FormBody.Builder()
                .add("question", question)
                .build();

        Request request = new Request.Builder()
                .url(API_URL)
                .post(requestBody)
                .build();

        client.newCall(request).enqueue(new Callback() {
            @Override public void onFailure(Call call, IOException e) {
                Log.e("ASK", "API call failed", e);
                mainHandler.post(() -> responseView.setText("Failed to connect: " + e.getMessage()));
            }

            @Override public void onResponse(Call call, Response response) throws IOException {
                if (!response.isSuccessful()) {
                    mainHandler.post(() -> responseView.setText("Error: " + response.code()));
                } else {
                    String responseText = response.body().string();
                    mainHandler.post(() -> responseView.setText("Response:\n" + responseText));
                }
            }
        });
    }
}
