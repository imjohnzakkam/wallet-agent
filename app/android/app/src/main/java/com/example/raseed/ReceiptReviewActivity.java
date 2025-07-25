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

        // Build your request body and make the API call here using Retrofit or OkHttp
        // TODO : Build request body here
        // You can use JSONObject or a request class depending on your setup

        Toast.makeText(this, "Sending to wallet...", Toast.LENGTH_SHORT).show();
        // Call your API here
    }
}
