# Testing Platform - Automated Exam System

A comprehensive automated testing platform with Telegram bot integration, web interface, and admin panel.

## 🚀 Features

- **Telegram Bot Interface**: Students register and access tests via Telegram
- **Web Test Interface**: Clean, responsive UI for taking tests with countdown timer
- **Auto-Grading**: Multiple choice questions graded automatically
- **Manual Grading**: Teachers grade written answers through admin panel
- **Anti-Cheat**: One attempt per student, session-based access
- **Export System**: Download results as Excel or PDF
- **Session Management**: 90-minute timer with auto-submit

## 📋 Tech Stack

- **Backend**: FastAPI (Python)
- **Bot**: Aiogram 3.x
- **Database**: PostgreSQL
- **Frontend**: HTML/CSS/JavaScript
- **Authentication**: JWT
- **Export**: openpyxl, reportlab
- **Deployment**: Docker Compose

## 🛠️ Quick Start

> **Production (Contabo VPS, Docker + HTTPS):** [DEPLOY_CONTABO.md](DEPLOY_CONTABO.md) qo'llanmasiga qarang.

### Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (from @BotFather)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd testing-platform
```

2. **Create environment file**
```bash
cp backend/.env.example backend/.env
cp bot/.env.example bot/.env
```

3. **Configure environment variables**

Edit `backend/.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/testing_platform
SECRET_KEY=your-super-secret-key-here
```

Edit `bot/.env`:
```env
BOT_TOKEN=your-telegram-bot-token
BACKEND_URL=http://backend:8000
WEB_APP_URL=http://your-domain.com:8000
```

4. **Start services**
```bash
docker-compose up -d
```

5. **Initialize database**
```bash
docker-compose exec backend python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
```

6. **Create admin user**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123",
    "role": "admin"
  }'
```

## 📱 Usage

### For Students (via Telegram Bot)

1. Start the bot: `/start`
2. Register: `/register` - provide name, surname, region
3. Click "🚀 Start Test"
4. Enter test code provided by teacher
5. Click the link to open test in browser
6. Complete test within 90 minutes
7. View results: "📊 My Results"

### For Teachers (Admin Panel)

1. Open `http://localhost:8000/static/admin/`
2. Login with admin credentials
3. **Create Test**:
   - Click "Create New Test"
   - Enter test code, title, description
   - Set MCQ answers (1-35)
   - Submit
4. **Grade Written Answers**:
   - Go to "Grade Written Answers"
   - Review student answers
   - Assign scores and comments
5. **Export Results**:
   - Go to "Manage Tests"
   - Click "Export Excel" or "Export PDF"

## 📁 Project Structure

```
testing-platform/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── models/       # Database models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   └── utils/        # Helpers
│   ├── static/           # Frontend files
│   │   ├── student/      # Test interface
│   │   └── admin/        # Admin panel
│   └── requirements.txt
├── bot/
│   ├── handlers/         # Bot command handlers
│   ├── keyboards/        # Bot keyboards
│   ├── states/           # FSM states
│   └── bot.py
├── docker-compose.yml
└── README.md
```

## 🔧 API Endpoints

### Public
- `POST /api/v1/users/register` - Register student
- `GET /api/v1/tests/code/{code}` - Get test by code
- `POST /api/v1/sessions/start` - Start test session
- `POST /api/v1/results/submit` - Submit test

### Admin (requires JWT)
- `POST /api/v1/auth/login` - Admin login
- `POST /api/v1/tests/` - Create test
- `GET /api/v1/admin/students` - List students
- `POST /api/v1/admin/grade-written` - Grade answer
- `GET /api/v1/admin/export/{id}/excel` - Export Excel
- `GET /api/v1/admin/export/{id}/pdf` - Export PDF

## 🔒 Security Features

- JWT authentication for admins
- bcrypt password hashing
- CORS protection
- Session token validation
- One attempt per test (DB constraint)
- Server-side timer validation

## 📊 Database Schema

- **users**: Student information
- **admin_users**: Teacher/admin accounts
- **tests**: Test definitions
- **answer_keys**: Correct answers (JSONB)
- **test_sessions**: Active sessions with timers
- **results**: Student scores
- **mcq_answers**: Individual MCQ responses
- **written_answers**: Essay responses
- **written_reviews**: Teacher grading

## 🐛 Troubleshooting

**Bot not responding?**
- Check bot token in `.env`
- Verify bot service is running: `docker-compose ps`
- Check logs: `docker-compose logs bot`

**Database connection error?**
- Ensure PostgreSQL is healthy: `docker-compose ps db`
- Check DATABASE_URL in backend/.env

**Frontend not loading?**
- Clear browser cache
- Check backend logs: `docker-compose logs backend`
- Verify static files are mounted correctly

## 📈 Production Deployment

1. Use PostgreSQL migrations (Alembic)
2. Set strong SECRET_KEY
3. Use reverse proxy (Nginx)
4. Enable HTTPS
5. Configure firewall rules
6. Set up backup for PostgreSQL
7. Use production WSGI server (Gunicorn)

## 📝 License

MIT License

## 👨‍💻 Contributing

Pull requests are welcome!

## 📧 Support

For issues and questions, please open a GitHub issue.
