# Open Threads Reminder

A Slack bot that tracks inactive threads and sends AI-powered reminders.

## Quick Setup

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Environment Variables
Create `.env` file:
```bash
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### 3. Configure Settings
Edit `config.py`:
- Set your database credentials in `DB_CONFIG`
- Add your Slack channels in `channels` array
- Set `TESTING_MODE = True` for quick testing

### 4. Initialize Database
```bash
python initialize.py
```

### 5. Run the Bot
```bash
python main.py
```

## Dashboard (Optional)
```bash
cd dashboard
go run main.go
```
Access server host and port at: http://127.0.0.1:18080

### Frontend Development
```bash
cd dashboard/ui
npm install
npm run dev
```
Access UI at: http://127.0.0.1:5173

## Requirements
- Python 3.8+
- PostgreSQL/YugabyteDB
- Slack Bot Token
- Google Cloud Project with Vertex AI enabled
