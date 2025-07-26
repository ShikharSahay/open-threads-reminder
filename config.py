THREAD_CYCLE = 90
RESPONSE_LIMIT = 7

# 🧪 TESTING CONFIGURATION
# Set TESTING_MODE = True for quick testing with minutes instead of days
TESTING_MODE = True  # Set to False for production

# Testing values (when TESTING_MODE = True)
TESTING_RESPONSE_LIMIT = 5  # 5 minutes for testing
TESTING_THREAD_CYCLE = 60   # 60 minutes (1 hour) for testing
TESTING_TIME_UNIT = "minutes"
TESTING_BOT_COOLDOWN = 2    # 2 minutes between bot messages (testing)

# Production values (when TESTING_MODE = False)  
PRODUCTION_RESPONSE_LIMIT = 7  # 7 days for production
PRODUCTION_THREAD_CYCLE = 90   # 90 days for production
PRODUCTION_TIME_UNIT = "days"
PRODUCTION_BOT_COOLDOWN = 24   # 24 hours between bot messages (production)

# Active configuration (automatically set based on TESTING_MODE)
if TESTING_MODE:
    ACTIVE_RESPONSE_LIMIT = TESTING_RESPONSE_LIMIT
    ACTIVE_THREAD_CYCLE = TESTING_THREAD_CYCLE
    ACTIVE_TIME_UNIT = TESTING_TIME_UNIT
    ACTIVE_BOT_COOLDOWN = TESTING_BOT_COOLDOWN
    print(f"🧪 TESTING MODE: Using {ACTIVE_RESPONSE_LIMIT} {ACTIVE_TIME_UNIT} inactivity threshold")
    print(f"🤖 Bot cooldown: {ACTIVE_BOT_COOLDOWN} {ACTIVE_TIME_UNIT} between messages")
else:
    ACTIVE_RESPONSE_LIMIT = PRODUCTION_RESPONSE_LIMIT  
    ACTIVE_THREAD_CYCLE = PRODUCTION_THREAD_CYCLE
    ACTIVE_TIME_UNIT = PRODUCTION_TIME_UNIT
    ACTIVE_BOT_COOLDOWN = PRODUCTION_BOT_COOLDOWN
    print(f"🚀 PRODUCTION MODE: Using {ACTIVE_RESPONSE_LIMIT} {ACTIVE_TIME_UNIT} inactivity threshold")
    print(f"🤖 Bot cooldown: {ACTIVE_BOT_COOLDOWN} hours between messages")

DB_CONFIG = {
    "dbname": "yugabyte", 
    "user": "yugabyte", 
    "password": "Threads@123", 
    "host": "10.150.3.246",
    "port": "5433"
}
DB_NAME = "open_thread_db"
channels = [
    {
        "channel_name":"krishna-slack-test",
        "channel_id":"C097FBZTT8T"
    }
]