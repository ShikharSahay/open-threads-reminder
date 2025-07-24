from slack.fetcher import SlackFetcher

if __name__ == "__main__":
    channel_id = "C0976QAJU3F"
    fetcher = SlackFetcher()

    all_threads = fetcher.fetch_all_threads(channel_id=channel_id, days=90)
    
    # Sort threads by timestamp (optional: in case API doesn't return ordered)
    sorted_threads = sorted(all_threads, key=lambda x: float(x["thread_ts"]), reverse=True)
    
    last_2_threads = sorted_threads[:2]

    for thread in last_2_threads:
        print(f"\n🧵 Thread TS: {thread['thread_ts']}")
        for msg in thread['messages']:
            print(f"  ➤ {msg.get('user', 'unknown')}: {msg.get('text')}")
