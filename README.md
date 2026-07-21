# MailPilot AI 📧🤖

> An AI-powered email assistant that organizes your inbox, summarizes emails, detects important messages, extracts deadlines, creates reminders, and lets you interact with your email using natural voice.

---

# Overview

MailPilot AI transforms traditional email into an intelligent assistant.

Instead of manually reading every email, MailPilot AI automatically:

* 📬 Organizes incoming emails
* 🧠 Generates AI summaries
* ⭐ Scores email importance
* ✅ Detects action-required emails
* 📅 Extracts deadlines and meetings
* ⏰ Creates smart reminders
* 🛡️ Detects phishing or suspicious emails
* 🎙️ Lets users ask questions using voice

The goal is to reduce email overload and help users focus only on what matters.

---

# Features

## Email Management

* Secure Gmail OAuth login
* Automatic email synchronization
* AI-powered email categorization
* Email importance scoring (0–100)
* Smart summaries
* Search emails

## AI Assistant

* AI-generated summaries
* Action-required detection
* Deadline extraction
* Meeting detection
* Reminder generation
* Proactive suggestions

## Voice Assistant

Users can naturally ask:

* "What important emails do I have today?"
* "Do I have any interview invitations?"
* "What meetings are scheduled?"
* "Summarize today's inbox."

Speech is converted to text, analyzed by AI, and returned as a natural response.

## Notifications

* Push notifications for important emails
* Reminder notifications
* In-app notifications

## Security

* Gmail OAuth 2.0
* Encrypted OAuth tokens
* HTTPS communication
* Secure API authentication
* User data isolation

---

# Architecture

```text
                 Gmail API
                     │
              OAuth Authentication
                     │
          Email Synchronization Service
                     │
               AI Processing Queue
                     │
        ┌────────────┴────────────┐
        │                         │
 AI Classification         Deadline Detection
        │                         │
        └────────────┬────────────┘
                     │
               PostgreSQL Database
                     │
          Django REST Framework API
                     │
      ┌──────────────┴──────────────┐
      │                             │
 React Native App          Voice Assistant
      │                             │
      └───────────Push Notifications───────────
```

---

# Tech Stack

## Backend

* Python
* Django
* Django REST Framework
* Django Channels
* PostgreSQL
* Redis
* Celery
* Docker

## Mobile

* React Native
* Expo
* TypeScript
* Expo Router

## AI

* GPT-5.6
* Codex
* Whisper Speech-to-Text
* OpenRouter

## APIs

* Gmail API
* Google OAuth 2.0

---

# Project Structure

```text
backend/
    apps/
    config/
    requirements/

mobile/
    src/
    app/
    components/
    features/

docker-compose.yml
README.md
```

---

# Installation

## Clone Repository

```bash
git clone https://github.com/madarduale/mailpilot-ai.git

cd mailpilot-ai
```

---

## Backend

Install dependencies

```bash
pip install -r requirements.txt
```

Run migrations

```bash
python manage.py migrate
```

Start server

```bash
python manage.py runserver
```

---

## Mobile

Install dependencies

```bash
npm install
```

Start Expo

```bash
npx expo start
```

---

## Docker

```bash
docker compose up --build
```

---

# Environment Variables

Example:

```env
SECRET_KEY=

DEBUG=True

DATABASE_URL=

REDIS_URL=

OPENAI_API_KEY=

OPENAI_BASE_URL=

OPENAI_RESPONSES_MODEL=

OPENAI_TRANSCRIPTION_MODEL=

GOOGLE_OAUTH_CLIENT_ID=

GOOGLE_OAUTH_CLIENT_SECRET=

GOOGLE_OAUTH_REDIRECT_URI=

GOOGLE_OAUTH_SCOPES=

FCM_SERVER_KEY=
```

---

# Using the App

1. Login
2. Connect Gmail
3. Allow notification permissions
4. Synchronize emails
5. View AI summaries
6. Accept AI suggestions
7. Ask the voice assistant questions
8. Receive reminders and notifications

---

# Example AI Workflow

```text
New Email

↓

Email Sync

↓

AI Analysis

↓

Summary

↓

Importance Score

↓

Deadline Extraction

↓

Reminder

↓

Push Notification
```

---

# How GPT-5.6 Was Used

GPT-5.6 was used to:

* Design AI prompts
* Generate structured email analysis
* Summarize emails
* Detect deadlines
* Classify email importance
* Detect action-required tasks
* Generate reminder content
* Power the conversational voice assistant

---

# How Codex Was Used

Codex accelerated development throughout the project by assisting with:

* Backend API development
* Django models
* Database migrations
* OAuth implementation
* Mobile UI development
* API integration
* AI workflow implementation
* Refactoring
* Bug fixing
* Testing
* Code optimization

The majority of the application's implementation was completed using Codex with GPT-5.6.

---

# Challenges

Some challenges included:

* Gmail OAuth configuration
* Secure OAuth token management
* Background email synchronization
* AI prompt engineering
* Reminder scheduling
* Push notification integration
* Voice assistant implementation
* Expo SDK compatibility
* Cross-platform mobile development

---

# Future Improvements

* Microsoft Outlook support
* Yahoo Mail support
* AI-generated replies
* Floating Android assistant
* Calendar synchronization
* Multi-language support
* Offline AI capabilities
* Enterprise email providers
* Smarter proactive assistant
* Team collaboration

---

# License

This project was developed for the OpenAI Build Week Hackathon.

---

# Acknowledgements

Special thanks to:

* OpenAI
* Codex
* GPT-5.6
* Google Gmail API
* Expo
* Django
* React Native

for providing the technologies that made MailPilot AI possible.
