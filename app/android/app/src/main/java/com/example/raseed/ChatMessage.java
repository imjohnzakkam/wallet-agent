package com.example.raseed;

public class ChatMessage {
    private String text;
    private boolean isUser;
    private String walletLink;
    private boolean isMarkdown;

    public ChatMessage(String text, boolean isUser, String walletLink, boolean isMarkdown) {
        this.text = text;
        this.isUser = isUser;
        this.walletLink = walletLink;
        this.isMarkdown = isMarkdown;

    }

    public ChatMessage(String text, boolean isUser) {
        this(text, isUser, null, true);
    }

    public boolean isMarkdown() {
        return isMarkdown;
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
