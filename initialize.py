from db.init_db import DBClient
from config import DB_CONFIG, DB_NAME, channels

def initialize_enhanced_database():
    """Initialize the database with enhanced schema for dashboard."""
    
    print("🚀 Initializing enhanced database schema...")
    
    # Connect to database without specifying a database first
    init_config = DB_CONFIG.copy()
    if "dbname" in init_config:
        del init_config["dbname"]
    
    db = DBClient(init_config)
    
    try:
        # Create database and all tables with enhanced schema
        db.create_prerequisites(DB_NAME, channels)
        
        print("✅ Database initialization completed!")
        print("\nCreated/Updated:")
        print("  📊 Master channels table")
        print("  👥 User profiles cache table")
        print("  🧵 Enhanced channel tables with AI analysis columns")
        
        # Test the setup by checking channels
        print("\n🔍 Verifying setup...")
        all_channels = db.get_all_channels()
        print(f"  - Found {len(all_channels)} channels configured")
        
        for channel in all_channels:
            print(f"    📢 {channel['channel_name']} -> {channel['table_name']}")
        
        print("\n🎯 Enhanced features available:")
        print("  ✨ AI-generated thread names and descriptions")
        print("  🎭 Cached Slack user profiles with display pictures")
        print("  🏷️ Automated stakeholder extraction")
        print("  📈 Channel statistics tracking")
        print("  🔗 GitHub/Thread issue linking support")
        
    except Exception as e:
        print(f"❌ Error during initialization: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    initialize_enhanced_database()
