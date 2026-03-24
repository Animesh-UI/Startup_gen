# 🚀 AI Startup Portfolio & Fundraising Analytics Platform

## 🧠 Overview

An AI-powered web application that transforms startup ideas into structured plans, tracks business metrics, and simulates fundraising — all in one dashboard.

---

## ✨ Features

* 📝 Startup registration (problem, industry, stage)
* 🤖 AI-generated insights (audience, features, roadmap, funding)
* 📊 Realtime analytics (visitors, signups, revenue)
* 💰 Fundraising simulation with dynamic goals
* 📁 Portfolio management (multiple startups)

---

## 🛠️ Tech Stack

* Backend: Flask (Python)
* Database: SQLite (SQLAlchemy)
* AI: Groq API (LLM)
* Frontend: HTML, CSS

---

## 🏗️ Architecture Diagram

```
        +-------------------+
        |   User (Browser)  |
        +---------+---------+
                  |
                  v
        +-------------------+
        |   Flask Backend   |
        |-------------------|
        | Routes / Logic    |
        | AI Integration    |
        +----+--------+-----+
             |        |
             v        v
     +-----------+   +------------------+
     |  SQLite   |   |   Groq API (LLM) |
     | Database  |   |  AI Generation   |
     +-----------+   +------------------+
```

---

## 🔄 Application Flow

```
User Input (Startup Idea)
        |
        v
Store in Database
        |
        v
Send Problem → AI (Groq)
        |
        v
Generate:
- Audience
- Features
- Roadmap
- Funding Plan
        |
        v
Display on Dashboard
        |
        v
User Actions:
- Simulate Growth
- Add Funding
        |
        v
Update Metrics + Fundraising
        |
        v
Render Updated Analytics
```

---

## 📊 Database Schema

### Startup

```
id | name | problem | industry | stage
```

### Metrics

```
id | startup_id | visitors | signups | revenue
```

### Fundraising

```
id | startup_id | goal | raised | goal_set
```

---

## 🚀 How to Run

```bash
pip install flask flask_sqlalchemy python-dotenv openai
python main.py
```

Create `.env` file:

```
GROQ_API_KEY=your_api_key
```

---

## 💡 Future Enhancements

* 📈 Charts & graphs (Chart.js)
* 🔐 User authentication
* 🌐 Deployment (Render/Vercel)
* 🧠 AI startup scoring
* 🏦 Investor simulation (VC/Angel)

---

## 📌 One-Line Pitch

AI-powered platform to build, analyze, and simulate startup growth and fundraising in real time.
