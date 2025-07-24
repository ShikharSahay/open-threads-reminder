from slack.fetcher import SlackFetcher
import json

if __name__ == "__main__":
    channel_id = "C0979N7KD28"
    fetcher = SlackFetcher()

    threads = fetcher.fetch_full_threads(channel_id=channel_id, days=90)

    # Optional: sort by latest
    sorted_threads = sorted(threads, key=lambda x: float(x["thread_ts"]), reverse=True)

    for thread in sorted_threads[:5]:
        print(f"\n🧵 Thread TS: {thread['thread_ts']}")
        for i, msg in enumerate(thread['messages']):
            tag = "Parent" if i == 0 else "Reply"
            print(f"  {tag} ➤ {msg.get('user', 'unknown')}: {msg.get('text')}")

    # Write full JSON
    with open("threads_output.json", "w") as f:
        json.dump(threads, f, indent=2)
