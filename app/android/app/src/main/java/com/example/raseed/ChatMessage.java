package com.example.raseed;

public class ChatMessage {
    private String text;
    private boolean isUser;
    private String walletLink;

    public ChatMessage(String text, boolean isUser, String walletLink) {
        this.text = text;
        this.isUser = isUser;
        this.walletLink = walletLink;
    }

    public ChatMessage(String text, boolean isUser) {
        this(text, isUser, null);
    }

    public String getText() {
        return text;
    }

    public boolean isUser() {
        return isUser;
    }

    public String getWalletLink() {
        return walletLink;
    }
}
