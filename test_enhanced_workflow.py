from db.init_db import DBClient
from slack_services.init_slack import SlackService
from config import DB_CONFIG, DB_NAME, channels
import json

def test_enhanced_workflow():
    """Test the enhanced workflow with AI analysis and user profiles."""
    
    print("🧪 Testing Enhanced Thread Workflow")
    print("=" * 50)
    
    # Set up database connection
    DB_CONFIG["dbname"] = DB_NAME
    db = DBClient(DB_CONFIG)
    slack_service = SlackService()
    
    try:
        # Test 1: Check database schema
        print("\n1️⃣ Testing Database Schema...")
        
        channels_data = db.get_all_channels()
        print(f"✅ Found {len(channels_data)} channels in master table")
        
        for channel in channels_data:
            print(f"   📢 {channel['channel_name']} (Threads: {channel.get('thread_count', 0)})")
        
        # Test 2: Check enhanced thread data
        print("\n2️⃣ Testing Thread Data with AI Analysis...")
        
        for channel in channels:
            table_name = channel["channel_name"].replace("-", "_")
            
            # Get a sample thread with AI analysis
            query = f"""
                SELECT thread_ts, ai_thread_name, ai_description, ai_stakeholders, 
                       ai_priority, ai_confidence, github_issue, jira_ticket, thread_issue,
                       status, reply_count, latest_reply
                FROM {table_name} 
                WHERE ai_thread_name IS NOT NULL 
                LIMIT 3
            """
            
            try:
                db.cursor.execute(query)
                threads = db.cursor.fetchall()
                
                print(f"\n   📊 Sample threads from {channel['channel_name']}:")
                
                if not threads:
                    print("   ⚠️  No threads with AI analysis found yet")
                    continue
                
                for thread in threads:
                    print(f"   🧵 {thread['ai_thread_name']}")
                    print(f"      📝 {thread['ai_description']}...")
                    print(f"      🎯 Priority: {thread['ai_priority']} (Confidence: {thread['ai_confidence']})")
                    
                    # Parse stakeholders
                    try:
                        stakeholders = json.loads(thread['ai_stakeholders'] or '[]')
                        print(f"      👥 Stakeholders: {len(stakeholders)} users")
                    except json.JSONDecodeError:
                        print(f"      👥 Stakeholders: Data parsing error")
                    
                    # Show all issue references
                    issue_refs = []
                    if thread['github_issue']:
                        issue_refs.append(f"GitHub: {thread['github_issue']}")
                    if thread['jira_ticket']:
                        issue_refs.append(f"Jira: {thread['jira_ticket']}")
                    if thread['thread_issue']:
                        issue_refs.append(f"Thread: {thread['thread_issue']}")
                    
                    if issue_refs:
                        print(f"      🔗 Issues: {' | '.join(issue_refs)}")
                    
                    print(f"      📊 Status: {thread['status']} | Replies: {thread['reply_count']}")
                    print()
                    
            except Exception as e:
                print(f"   ❌ Error querying {table_name}: {e}")
        
        # Test 3: Check user profiles cache
        print("\n3️⃣ Testing User Profiles Cache...")
        
        profile_query = """
            SELECT user_id, display_name, real_name, profile_image_url, last_updated
            FROM user_profiles 
            ORDER BY last_updated DESC 
            LIMIT 5
        """
        
        try:
            db.cursor.execute(profile_query)
            profiles = db.cursor.fetchall()
            
            if profiles:
                print(f"✅ Found {len(profiles)} cached user profiles:")
                for profile in profiles:
                    print(f"   👤 {profile['display_name']} (@{profile['user_id']})")
                    print(f"      📸 Profile Image: {'✅ Available' if profile['profile_image_url'] else '❌ Missing'}")
                    print(f"      🕐 Last Updated: {profile['last_updated']}")
                    print()
            else:
                print("⚠️  No user profiles cached yet")
                
        except Exception as e:
            print(f"❌ Error querying user profiles: {e}")
        
        # Test 4: Test Slack API integration with issue extraction
        print("\n4️⃣ Testing Slack API Integration & Issue Extraction...")
        
        try:
            # Test user extraction from sample conversation
            sample_conversation = "[User: U123ABC456]: Hello team\n[User: U789DEF012]: Working on the API fix"
            extracted_users = slack_service.extract_user_ids_from_conversation(sample_conversation)
            print(f"✅ User extraction test: Found {len(extracted_users)} users: {extracted_users}")
            
            # Test GitHub issue extraction
            github_test = "Check out myorg/repo#123 and also https://github.com/team/project/issues/456"
            github_issues = slack_service.extract_github_issues_from_conversation(github_test)
            print(f"✅ GitHub extraction test: Found {len(github_issues)} issues: {github_issues}")
            
            # Test Jira ticket extraction  
            jira_test = "See PROJ-123 and also https://company.atlassian.net/browse/TEAM-456"
            jira_tickets = slack_service.extract_jira_tickets_from_conversation(jira_test)
            print(f"✅ Jira extraction test: Found {len(jira_tickets)} tickets: {jira_tickets}")
            
            # Test thread issue extraction
            thread_test = "Related to #789 and #101 but not myorg/repo#123"
            thread_issues = slack_service.extract_thread_issues_from_conversation(thread_test)
            print(f"✅ Thread extraction test: Found {len(thread_issues)} issues: {thread_issues}")
            
            # Test comprehensive extraction
            combined_test = "Working on PROJ-123 for myorg/repo#456 and see thread #789"
            all_refs = slack_service.extract_all_issue_references(combined_test)
            print(f"✅ Combined extraction test:")
            print(f"   GitHub: {all_refs['github_issues']}")
            print(f"   Jira: {all_refs['jira_tickets']}")
            print(f"   Thread: {all_refs['thread_issues']}")
            
            # Test rate limiting configuration
            print(f"✅ Rate limiting configured: {slack_service.DEFAULT_CONFIG['request_limit']} req/min")
            print(f"✅ Max retries: {slack_service.DEFAULT_CONFIG['max_retries']}")
            
        except Exception as e:
            print(f"❌ Slack API test error: {e}")
        
        # Test 5: Summary
        print("\n5️⃣ Workflow Summary...")
        
        # Count total threads with AI analysis
        total_analyzed = 0
        total_threads = 0
        
        for channel in channels:
            table_name = channel["channel_name"].replace("-", "_")
            
            try:
                db.cursor.execute(f"SELECT COUNT(*) as total FROM {table_name}")
                total = db.cursor.fetchone()['total']
                total_threads += total
                
                db.cursor.execute(f"SELECT COUNT(*) as analyzed FROM {table_name} WHERE ai_thread_name IS NOT NULL")
                analyzed = db.cursor.fetchone()['analyzed']
                total_analyzed += analyzed
                
            except Exception as e:
                print(f"Warning: Could not count threads in {table_name}: {e}")
        
        print(f"📊 Total threads: {total_threads}")
        print(f"🤖 AI analyzed: {total_analyzed}")
        print(f"📈 Analysis coverage: {(total_analyzed/total_threads*100) if total_threads > 0 else 0:.1f}%")
        
        print("\n🎉 Enhanced workflow is ready!")
        print("🚀 Run 'python main.py' to process threads with AI analysis")
        print("📊 Dashboard data will be populated automatically")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    test_enhanced_workflow() 