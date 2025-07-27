package com.example.raseed;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.net.Uri;
import android.os.Handler;
import android.os.IBinder;
import android.os.Looper;
import android.util.Log;
import androidx.core.app.NotificationCompat;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class WalletCronService extends Service {
    private static final String TAG = "WalletCronService";
    private static final String CHANNEL_ID = "wallet_channel";
    private static final String API_URL = "https://wallet-agent-203063692416.asia-south1.run.app/insights";
    private static final int NOTIFICATION_ID = 1;

    private Handler handler;
    private Runnable cronRunnable;
    private ExecutorService executor;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
        handler = new Handler(Looper.getMainLooper());
        executor = Executors.newSingleThreadExecutor();

        // Create the recurring task
        cronRunnable = new Runnable() {
            @Override
            public void run() {
                fetchWalletData();
                // Schedule next execution in 60 seconds
                handler.postDelayed(this, 60000);
            }
        };
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "Wallet cron service started");

        // Start the foreground service
        startForeground(NOTIFICATION_ID, createForegroundNotification());

        // Start the cron job
        handler.post(cronRunnable);

        return START_STICKY; // Restart if killed
    }

    private void fetchWalletData() {
        executor.execute(() -> {
            try {
                Log.d(TAG, "Fetching wallet data...");

                URL url = new URL(API_URL);
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setConnectTimeout(10000);
                conn.setReadTimeout(10000);

                int responseCode = conn.getResponseCode();
                if (responseCode == 200) {
                    BufferedReader reader = new BufferedReader(new InputStreamReader(conn.getInputStream()));
                    StringBuilder response = new StringBuilder();
                    String line;

                    while ((line = reader.readLine()) != null) {
                        response.append(line);
                    }
                    reader.close();

                    // Parse JSON response
                    JSONObject json = new JSONObject(response.toString());
                    String walletLink = json.optString("wallet_link");

                    if (walletLink != null && !walletLink.isEmpty()) {
                        showWalletNotification(walletLink);
                        Log.d(TAG, "Wallet notification sent: " + walletLink);
                    }
                } else {
                    Log.e(TAG, "API call failed with code: " + responseCode);
                }

            } catch (Exception e) {
                Log.e(TAG, "Error fetching wallet data", e);
            }
        });
    }

    private void showWalletNotification(String walletLink) {
        // Create intent to open wallet link
        Intent walletIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(walletLink));
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, walletIntent, PendingIntent.FLAG_IMMUTABLE);

        // Build notification
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("New monthly insights discovered")
                .setContentText("Tap to add to your wallet")
                .setPriority(NotificationCompat.PRIORITY_DEFAULT)
                .setAutoCancel(true)
                .addAction(android.R.drawable.ic_input_add, "Add to Wallet", pendingIntent);

        NotificationManager notificationManager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        notificationManager.notify((int) System.currentTimeMillis(), builder.build());
    }

    private Notification createForegroundNotification() {
        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("Wallet Monitor")
                .setContentText("Monitoring for wallet insights...")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .build();
    }

    private void createNotificationChannel() {
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "Wallet Insights",
                NotificationManager.IMPORTANCE_DEFAULT
        );
        NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        manager.createNotificationChannel(channel);
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        if (handler != null && cronRunnable != null) {
            handler.removeCallbacks(cronRunnable);
        }
        if (executor != null) {
            executor.shutdown();
        }
        Log.d(TAG, "Wallet cron service stopped");
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}