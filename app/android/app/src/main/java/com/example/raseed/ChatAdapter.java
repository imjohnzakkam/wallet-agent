package com.example.raseed;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.util.Log;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import java.util.List;

import io.noties.markwon.Markwon;
import io.noties.markwon.linkify.LinkifyPlugin;

public class ChatAdapter extends RecyclerView.Adapter<ChatAdapter.ChatViewHolder> {

    private List<ChatMessage> chatMessages;
    private OnMessageLongClickListener longClickListener;
    private Markwon markwon;

    // Interface for long click handling
    public interface OnMessageLongClickListener {
        void onMessageLongClick(ChatMessage message, View view);
    }

    public ChatAdapter(List<ChatMessage> chatMessages, OnMessageLongClickListener longClickListener, Context context) {
        this.chatMessages = chatMessages;
        this.longClickListener = longClickListener;
        this.markwon = Markwon.builder(context)
                .usePlugin(LinkifyPlugin.create())
                .build();
    }

    // Overloaded constructor for backward compatibility
    public ChatAdapter(List<ChatMessage> chatMessages) {
        this.chatMessages = chatMessages;
        this.longClickListener = null;
    }

    @NonNull
    @Override
    public ChatViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_chat_message, parent, false);
        return new ChatViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull ChatViewHolder holder, int position) {
        ChatMessage message = chatMessages.get(position);

        if (message.isMarkdown()) {
            // Render markdown
            markwon.setMarkdown(holder.messageText, message.getText());
        } else {
            // Set plain text
            holder.messageText.setText(message.getText());
        }

        holder.bind(message);
    }

    @Override
    public int getItemCount() {
        return chatMessages.size();
    }

    class ChatViewHolder extends RecyclerView.ViewHolder {
        private TextView messageText;
        private Button addToWalletButton;
        private LinearLayout bubbleLayout;

        public ChatViewHolder(@NonNull View itemView) {
            super(itemView);
            messageText = itemView.findViewById(R.id.messageText);
            addToWalletButton = itemView.findViewById(R.id.addToWalletButton);
            bubbleLayout = itemView.findViewById(R.id.bubbleLayout);
        }

        public void bind(ChatMessage message) {
            messageText.setText(message.getText());

            // Set up wallet button visibility and functionality for non-user messages with a valid wallet link
            if (!message.isUser() && message.getWalletLink() != null && !message.getWalletLink().isEmpty()) {
                addToWalletButton.setVisibility(View.VISIBLE);
                addToWalletButton.setOnClickListener(v -> {
                    Log.i("ChatAdapter", "Wallet link  raw: " + message.getWalletLink());
                    String url = message.getWalletLink();
                    if (!url.startsWith("http://") && !url.startsWith("https://")) {
                        url = "https://" + url; // ensure correct scheme
                    }

                    Log.i("ChatAdapter", "Wallet link : " + url);

                    Intent walletIntent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                    walletIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK); // safer context flag

                    if (walletIntent.resolveActivity(itemView.getContext().getPackageManager()) != null) {
                        itemView.getContext().startActivity(walletIntent);
                    } else {
                        Toast.makeText(itemView.getContext(), "No app found to open link", Toast.LENGTH_SHORT).show();
                    }
                });
            } else {
                addToWalletButton.setVisibility(View.INVISIBLE);
            }

            // Configure message bubble appearance based on sender
            if (message.isUser()) {
                // User message - align right, different color
                bubbleLayout.setGravity(Gravity.END);
                messageText.setBackgroundResource(R.drawable.user_chat_bubble); // You'll need this drawable
            } else {
                // Bot message - align left, default color
                bubbleLayout.setGravity(Gravity.START);
                messageText.setBackgroundResource(R.drawable.chat_bubble);
            }

            // Set up long click listener for received messages (non-user messages)
            if (!message.isUser() && longClickListener != null) {
                messageText.setOnLongClickListener(v -> {
                    longClickListener.onMessageLongClick(message, v);
                    return true; // Consume the long click event
                });

                // Also add long click to the entire bubble for better UX
                bubbleLayout.setOnLongClickListener(v -> {
                    longClickListener.onMessageLongClick(message, messageText);
                    return true;
                });
            } else {
                // Remove long click listeners for user messages
                messageText.setOnLongClickListener(null);
                bubbleLayout.setOnLongClickListener(null);
            }
        }
    }
}