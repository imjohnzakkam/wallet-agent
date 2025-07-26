package com.example.raseed;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.recyclerview.widget.RecyclerView;
import java.util.List;

public class ChatAdapter extends RecyclerView.Adapter<ChatAdapter.ViewHolder> {

    private List<ChatMessage> messages;
    private Context context;

    public ChatAdapter(List<ChatMessage> chatMessages) {
        messages = chatMessages;
    }

    public static class ViewHolder extends RecyclerView.ViewHolder {
        public TextView messageText;
        public LinearLayout bubbleLayout;
        public Button addToWalletButton;

        public ViewHolder(View view) {
            super(view);
            messageText = view.findViewById(R.id.messageText);
            bubbleLayout = view.findViewById(R.id.bubbleLayout);
            addToWalletButton = view.findViewById(R.id.addToWalletButton);
        }
    }

    @Override
    public ViewHolder onCreateViewHolder(ViewGroup parent, int viewType) {
        context = parent.getContext();  // for intent launch
        View view = LayoutInflater.from(context)
                .inflate(R.layout.item_chat_message, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(ViewHolder holder, int position) {
        ChatMessage msg = messages.get(position);

        // Set message text and alignment
        holder.messageText.setText(msg.getText());
        holder.bubbleLayout.setGravity(msg.isUser() ? Gravity.END : Gravity.START);

        // Show or hide the "Add to Wallet" button
        if (!msg.isUser() && msg.getWalletLink() != null && !msg.getWalletLink().isEmpty()) {
            holder.addToWalletButton.setVisibility(View.VISIBLE);
            holder.addToWalletButton.setOnClickListener(v -> {
                Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(msg.getWalletLink()));
                context.startActivity(intent);
            });
        } else {
            holder.addToWalletButton.setVisibility(View.GONE);
            holder.addToWalletButton.setOnClickListener(null);
        }
    }

    @Override
    public int getItemCount() {
        return messages.size();
    }
}
