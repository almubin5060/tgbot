import os
import tkinter as tk
from tkinter import scrolledtext
from flask import Flask, request, jsonify
import threading
import logging
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from openai import OpenAI

# Configuration - USE ENVIRONMENT VARIABLES IN PRODUCTION
CONFIG = {
    "TELEGRAM_TOKEN": os.getenv('TELEGRAM_TOKEN', '7948388480:AAEmBUKupcQN7COQaVHcBaTZ6k2aOYNdIwI'),  # REPLACE THIS!
    "OPENROUTER_API_KEY": os.getenv('OPENROUTER_API_KEY', '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'),
    "API_SECRET_KEY": os.getenv('API_SECRET_KEY', 'your-api-secret-here'),  # For Flask API auth
    "MODEL": "deepseek/deepseek-r1-distill-llama-70b:free",
    "HOST": "0.0.0.0",
    "PORT": 5000
}

class ChatApp:
    def __init__(self, root=None):
        # Initialize GUI if root is provided
        if root:
            self.setup_gui(root)
        
        # Initialize OpenAI client
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=CONFIG["OPENROUTER_API_KEY"],
        )
        
        # Initialize Telegram bot
        self.setup_telegram_bot()
        
        # Start Flask API server
        self.start_flask_server()

    def setup_gui(self, root):
        self.root = root
        self.root.title("AI Chat Bot")
        
        self.chat_history = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=60, height=20)
        self.chat_history.grid(row=0, column=0, columnspan=2, padx=10, pady=10)
        
        self.input_field = tk.Entry(root, width=50)
        self.input_field.grid(row=1, column=0, padx=10, pady=10)
        
        self.send_button = tk.Button(root, text="Send", command=self.send_message)
        self.send_button.grid(row=1, column=1, padx=10, pady=10)
        
        self.root.bind('<Return>', lambda event: self.send_message())

    def setup_telegram_bot(self):
        if not CONFIG["TELEGRAM_TOKEN"]:
            logging.warning("No Telegram token provided - Telegram bot disabled")
            return
            
        self.telegram_bot = Bot(token=CONFIG["TELEGRAM_TOKEN"])
        self.updater = Updater(token=CONFIG["TELEGRAM_TOKEN"], use_context=True)
        
        dp = self.updater.dispatcher
        dp.add_handler(CommandHandler("start", self.telegram_start))
        dp.add_handler(MessageHandler(Filters.text & ~Filters.command, self.telegram_message))
        
        self.telegram_thread = threading.Thread(target=self.updater.start_polling)
        self.telegram_thread.daemon = True
        self.telegram_thread.start()

    def start_flask_server(self):
        flask_app = Flask(__name__)
        
        @flask_app.route('/api/chat', methods=['POST'])
        def chat_api():
            # Basic API authentication
            if request.headers.get('X-API-KEY') != CONFIG["API_SECRET_KEY"]:
                return jsonify({"error": "Unauthorized"}), 401
                
            data = request.json
            user_input = data.get('message')
            if not user_input:
                return jsonify({"error": "No message provided"}), 400
            
            response = self.get_ai_response(user_input)
            return jsonify({"response": response})
        
        self.flask_thread = threading.Thread(
            target=lambda: flask_app.run(
                host=CONFIG["HOST"],
                port=CONFIG["PORT"],
                debug=False
            )
        )
        self.flask_thread.daemon = True
        self.flask_thread.start()

    def send_message(self, event=None):
        if hasattr(self, 'input_field'):
            user_input = self.input_field.get()
            if not user_input:
                return
                
            self.chat_history.insert(tk.END, f"You: {user_input}\n")
            self.input_field.delete(0, tk.END)
            response = self.get_ai_response(user_input)
            self.chat_history.insert(tk.END, f"AI: {response}\n\n")

    def telegram_start(self, update: Update, context: CallbackContext):
        update.message.reply_text('Hello! I am your AI assistant. Send me a message and I will respond.')

    def telegram_message(self, update: Update, context: CallbackContext):
        response = self.get_ai_response(update.message.text)
        update.message.reply_text(response)

    def get_ai_response(self, user_input):
        try:
            completion = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://your-vps-domain.com",
                    "X-Title": "AI Chat Assistant",
                },
                model=CONFIG["MODEL"],
                messages=[{"role": "user", "content": user_input}]
            )
            return completion.choices[0].message.content
        except Exception as e:
            logging.error(f"AI Error: {str(e)}")
            return f"Sorry, I encountered an error: {str(e)}"

if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    root = tk.Tk()
    app = ChatApp(root=root)
    root.mainloop()
