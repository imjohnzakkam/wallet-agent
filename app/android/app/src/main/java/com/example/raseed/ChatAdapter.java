package com.example.raseed;

import android.view.Gravity;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.TextView;

import androidx.recyclerview.widget.RecyclerView;
import java.util.List;

public class ChatAdapter extends RecyclerView.Adapter<ChatAdapter.ViewHolder> {

    private List<ChatMessage> messages;

    public ChatAdapter(List<ChatMessage> chatMessages) {
        messages = chatMessages;
    }

    public static class ViewHolder extends RecyclerView.ViewHolder {
        public TextView messageText;
        public LinearLayout bubbleLayout;

        public ViewHolder(View view) {
            super(view);
            messageText = view.findViewById(R.id.messageText);
            bubbleLayout = view.findViewById(R.id.bubbleLayout);
        }
    }

    @Override
    public ViewHolder onCreateViewHolder(ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(parent.getContext())
                .inflate(R.layout.item_chat_message, parent, false);
        return new ViewHolder(view);
    }

    @Override
    public void onBindViewHolder(ViewHolder holder, int position) {
        ChatMessage msg = messages.get(position);
        holder.messageText.setText(msg.getText());
        holder.bubbleLayout.setGravity(msg.isUser() ? Gravity.END : Gravity.START);
    }

    @Override
    public int getItemCount() {
        return messages.size();
    }
}

