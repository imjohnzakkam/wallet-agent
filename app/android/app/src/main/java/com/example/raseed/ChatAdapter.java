package com.example.raseed;

import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import java.util.List;

public class ChatAdapter extends RecyclerView.Adapter<ChatAdapter.ChatViewHolder> {

    private List<ChatMessage> chatMessages;
    private OnMessageLongClickListener longClickListener;

    // Interface for long click handling
    public interface OnMessageLongClickListener {
        void onMessageLongClick(ChatMessage message, View view);
    }

    public ChatAdapter(List<ChatMessage> chatMessages, OnMessageLongClickListener longClickListener) {
        this.chatMessages = chatMessages;
        this.longClickListener = longClickListener;
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

            // Set up wallet button visibility and functionality
            if (!message.isUser() && !message.getWalletLink().isEmpty()) {
                addToWalletButton.setVisibility(View.VISIBLE);
                addToWalletButton.setOnClickListener(v -> {
                    // Handle wallet link action
                    // You can implement wallet integration here
                });
            } else {
                addToWalletButton.setVisibility(View.GONE);
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