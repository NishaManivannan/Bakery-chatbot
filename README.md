# Bakery Chatbot 🍰

A Flask-based voice-enabled chatbot for handling bakery orders like cakes, cookies, and pizzas. The bot uses natural language input and provides audio responses using Google Text-to-Speech (gTTS).

 🚀 Features

- Voice-based chatbot using Flask + gTTS
- Session-based interaction with users
- Place, confirm, and cancel orders
- Dynamic pricing logic based on item and quantity
- Auto-generated MP3 audio responses
- Cleans up temporary audio files after each session

 📁 Project Structure

chatbot/
├── static/
│ └── audio/ # Temporary MP3 files
├── templates/
│ └── index.html # Chat UI
├── app.py # Main Flask backend
├── db.py # Order database logic
├── requirements.txt # Python dependencies
├── .gitignore # Ignored files
└── README.md # Project documentation
