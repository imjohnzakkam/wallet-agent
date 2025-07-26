package com.example.raseed;

import android.app.DatePickerDialog;
import android.app.TimePickerDialog;
import android.content.Intent;

import android.icu.util.Calendar;
import android.net.Uri;
import android.os.Bundle;

import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageView;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import org.json.JSONException;
import org.json.JSONObject;

import java.io.IOException;
import java.util.Locale;

import okhttp3.*;

public class ReceiptReviewActivity extends AppCompatActivity {

    private EditText vendorName, billCategory, receiptDate, receiptTime, totalAmount;
    private Button addToWalletBtn;
    private ImageView receiptImage;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_receipt_review);

        vendorName = findViewById(R.id.vendorName);
        billCategory = findViewById(R.id.billCategory);
        receiptDate = findViewById(R.id.receiptDate);
        receiptTime = findViewById(R.id.receiptTime);
        totalAmount = findViewById(R.id.totalAmount);
        addToWalletBtn = findViewById(R.id.addToWalletBtn);
        receiptImage = findViewById(R.id.receiptImage);

        // Receive and pre-fill data
        Intent intent = getIntent();
        vendorName.setText(intent.getStringExtra("vendor"));
        billCategory.setText(intent.getStringExtra("category"));
        receiptDate.setText(intent.getStringExtra("date"));
        receiptTime.setText(intent.getStringExtra("time"));
        totalAmount.setText(intent.getStringExtra("amount"));

        // If you're passing image Uri or Bitmap
        String imagePath = intent.getStringExtra("imagePath");
        if (imagePath != null) {
            receiptImage.setImageURI(Uri.parse(imagePath));
        }

        // Date picker
        receiptDate.setOnClickListener(v -> showDatePickerDialog());

        // Time picker
        receiptTime.setOnClickListener(v -> showTimePickerDialog());

        // Final API call with updated data
        addToWalletBtn.setOnClickListener(v -> submitFinalData());
    }

    private void showDatePickerDialog() {
        Calendar calendar = Calendar.getInstance();
        new DatePickerDialog(
                this,
                (view, year, month, dayOfMonth) ->
                        receiptDate.setText(String.format(Locale.getDefault(), "%04d-%02d-%02d", year, month + 1, dayOfMonth)),
                calendar.get(Calendar.YEAR),
                calendar.get(Calendar.MONTH),
                calendar.get(Calendar.DAY_OF_MONTH)
        ).show();
    }

    private void showTimePickerDialog() {
        Calendar calendar = Calendar.getInstance();
        new TimePickerDialog(
                this,
                (view, hourOfDay, minute) ->
                        receiptTime.setText(String.format(Locale.getDefault(), "%02d:%02d", hourOfDay, minute)),
                calendar.get(Calendar.HOUR_OF_DAY),
                calendar.get(Calendar.MINUTE),
                true
        ).show();
    }

    private void submitFinalData() {
        String vendor = vendorName.getText().toString();
        String category = billCategory.getText().toString();
        String date = receiptDate.getText().toString();
        String time = receiptTime.getText().toString();
        String amount = totalAmount.getText().toString();

        String receiptId = getIntent().getStringExtra("receipt_id");
        String userId = "123"; // or retrieve from SharedPreferences/auth system

        OkHttpClient client = new OkHttpClient();

        String json = "{"
                + "\"receipt_id\":\"" + receiptId + "\","
                + "\"user_id\":\"" + userId + "\","
                + "\"vendor\":\"" + vendor + "\","
                + "\"category\":\"" + category + "\","
                + "\"date\":\"" + date + "\","
                + "\"time\":\"" + time + "\","
                + "\"amount\":\"" + amount + "\""
                + "}";

        RequestBody body = RequestBody.create(json, MediaType.parse("application/json"));
        Request request = new Request.Builder()
                .url("https://wallet-agent-203063692416.asia-south1.run.app/add-to-wallet")
                .post(body)
                .build();

        Toast.makeText(this, "Sending to wallet...", Toast.LENGTH_SHORT).show();

        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onFailure(Call call, IOException e) {
                runOnUiThread(() -> Toast.makeText(ReceiptReviewActivity.this, "Failed to send: " + e.getMessage(), Toast.LENGTH_LONG).show());
            }

            @Override
            public void onResponse(Call call, Response response) throws IOException {
                if (!response.isSuccessful()) {
                    runOnUiThread(() -> Toast.makeText(ReceiptReviewActivity.this, "Server error: " + response.code(), Toast.LENGTH_LONG).show());
                    return;
                }

                String responseBody = response.body().string();
                try {
                    JSONObject jsonObject = new JSONObject(responseBody);
                    String walletLink = jsonObject.optString("wallet_link");

                    runOnUiThread(() -> {
                        Toast.makeText(ReceiptReviewActivity.this, "Receipt added to wallet!", Toast.LENGTH_LONG).show();

                        // Optionally open the link in browser
                        if (!walletLink.isEmpty()) {
                            Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(walletLink));
                            startActivity(intent);
                        }

                        // Finish activity or return to MainActivity
                        finish();
                    });
                } catch (JSONException e) {
                    runOnUiThread(() -> Toast.makeText(ReceiptReviewActivity.this, "Invalid response", Toast.LENGTH_LONG).show());
                }
            }
        });
    }

}
