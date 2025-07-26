# Open Threads Reminder 
 
The Open Threads Reminder AI agent tracks inactive slack threads and sends AI-powered reminders by classifying the open threads in a particular slack channel. This is useful for keeping track of all the open JIRA/Github tickets which haven't seen any activities after an extended period. This agent has the following capabilities - 

- Keep track of all the open converations in slack channel. 
- Agent uses LLMs to Classify and mark the thread status on a daily basis - Open, Closed, Duplicate.
- Send reminders on the slack channel to the stakeholders with AI generated Summary.
- UI Dashboard for reviewing the open converations and add new channels for tracking.
- RAG retrieval of Github issues, JIRA tickets and YugabyteDB Docs for identifying duplicate issues and potential inconsistencies in the YugabyteDB documentation.

Usecase 1: 

SDETs over the course of project execution would have raised several issues marked high or critical and it will be overwhelimg for the developer to keep track of all the slack conversations and high chances some slack threads fall through the cracks potentially leading to bugs introduced in the final release. The open threads Reminder AI agent keep tracks of all the threads open for a extended period and send reminders with to stakeholders that the assoicated Github/JIRA ticket is still open and has not seen any activity.

Usecase 2:
Agent can be used for keeping track of all the open converstations on the #yb-users channel in the community slack and send a summary to relevant folks about the open question along with Summary and potential answers. The potential answer can be used in responding to the user thread if the confidence score of the generated answer is >90%.

## Architecture

![Open Threads Architecture Diagram](screenshots/arc_diagram.svg)

## UI
![Open Threads Dashboard](screenshots/image_1.png)

Below are sample images showing tracked Slack threads:

| Thread Priorities | Open Thread |
|-------------|--------------|
| ![Priorities](screenshots/image_2.png) | ![Open Thread](screenshots/image_3.png) |


## Demo

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
