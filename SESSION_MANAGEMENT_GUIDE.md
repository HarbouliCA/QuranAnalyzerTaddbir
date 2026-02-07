# Session Management System - UPDATED GUIDE

## 🎉 Hybrid Storage System

Your Quran Analyzer now has a **robust hybrid storage system** that ensures conversation saving works **even when Neo4j is unavailable**.

### Automatic Fallback

The system automatically tries (in order):
1. **Neo4j Graph Database** (preferred) - Cloud-based, queryable, integrated
2. **Local JSON Storage** (fallback) - Stored in `./conversations/` folder

You'll see which system is active in the sidebar:
- 🌐 **متصل بـ Neo4j** = Using Neo4j (green)
- 📁 **التخزين المحلي (JSON)** = Using local files (blue)

---

## Why the Hybrid Approach?

### Neo4j Issues (What You're Experiencing)

The DNS error `[Errno 11001] getaddrinfo failed` means:
- Your computer can't reach `b612b258.databases.neo4j.io`
- Could be: network firewall, Neo4j Aura paused, DNS issues

**But don't worry!** The app now automatically uses local storage instead.

### Local Storage Benefits

✅ **Always works** - No network required
✅ **Fast** - Files on your disk
✅ **Portable** - Easy to backup/share
✅ **Private** - Never leaves your computer

### Neo4j Benefits (When It Works)

✅ **Cloud sync** - Access from anywhere
✅ **Advanced queries** - Cypher analytics
✅ **Integration** - Connected to Quran knowledge graph
✅ **Scalable** - Unlimited conversations

---

## How to Fix Neo4j Connection

### Option 1: Check Neo4j Aura Status

1. Go to [https://console.neo4j.io](https://console.neo4j.io)
2. Login with your account
3. Check if database `b612b258` is:
   - ✅ Running (green) - Good!
   - ⏸️ Paused (yellow) - Click "Resume"
   - ❌ Stopped (red) - Click "Start"

### Option 2: Update Connection String

If your database moved or changed:

1. Open `.env` file
2. Update the URI:
   ```
   NEO4J_URI=neo4j+ssc://YOUR-NEW-DATABASE.databases.neo4j.io:7687
   ```
3. Restart the app

### Option 3: Test Connection

Run diagnostics:
```bash
python test_session_manager.py
```

If it works, Neo4j is accessible!
If it fails, you'll see the error details.

---

## Using Local Storage (Current Setup)

Since Neo4j is currently unavailable, you're using local JSON storage.

### Where Are Files Stored?

All conversations are in: `./conversations/`

Example structure:
```
conversations/
├── index.json                    # Session index
├── uuid-1234.json               # Session 1
├── uuid-5678.json               # Session 2
└── ...
```

### Viewing Your Sessions Manually

Each session file contains:
```json
{
  "session_id": "uuid-here",
  "created_at": "2026-01-31T12:00:00",
  "user_name": "تدبر سورة ق",
  "verse_refs": "50:15-16",
  "initial_question": "...",
  "conversation": [
    {
      "role": "user",
      "content": "...",
      "timestamp": "..."
    },
    {
      "role": "assistant",
      "content": "...",
      "timestamp": "..."
    }
  ],
  "context_package": {...}
}
```

### Backup Your Conversations

Super easy! Just copy the `conversations/` folder:
```bash
# Backup
cp -r conversations/ conversations_backup/

# Or ZIP it
tar -czf conversations_backup.tar.gz conversations/
```

### Migrate to Neo4j Later

When Neo4j is available, conversations can be migrated.

*(Migration tool coming soon!)*

---

## Features (Same for Both Storage Types)

All session management features work identically:

### 💾 Save Conversations
- Auto-saves every question and answer
- Preserves context (related verses, concepts)

### 📂 Load Previous Sessions
- Browse last 10 sessions in sidebar
- Click to load and continue

### 🔍 Search
- Search by name, verse refs, or question
- Works across all saved sessions

### ✏️ Rename
- Give meaningful names to sessions
- E.g., "تدبر سورة ق - البعث والخلق"

### 🗑️ Delete
- Remove sessions you don't need
- Permanent deletion

---

## Switching Between Storage Types

### From Local to Neo4j

When Neo4j becomes available:
1. Fix the connection (see "How to Fix" above)
2. Restart the app
3. System will automatically use Neo4j for NEW sessions
4. Old local sessions remain in `conversations/`

*To migrate old sessions, use the migration tool (coming soon)*

### From Neo4j to Local

If Neo4j goes down:
1. System automatically falls back
2. You'll see "📁 التخزين المحلي (JSON)" in sidebar
3. All features continue working
4. Conversations saved locally

---

## Troubleshooting

### "No sessions showing up"

**Local Storage**:
- Check: Does `conversations/` folder exist?
- Check: Is `index.json` file present?
- Run: `python test_local_storage.py` to verify

**Neo4j**:
- Check: Is database running in Neo4j Aura?
- Run: `python test_session_manager.py` to test

### "Can't save conversations"

Check sidebar for error message.
- If "Neo4j غير متاح" → Using local (normal)
- If "خطأ في نظام الحفظ" → Check permissions on `conversations/` folder

### "Lost my conversations"

**Local Storage**:
- Check `conversations/` folder
- Look for `.json` files
- Restore from backup if you made one

**Neo4j**:
- Login to Neo4j Aura console
- Check database status
- Conversations are safe in the cloud

---

## Performance Notes

### Local Storage
- ✅ Instant save/load (disk speed)
- ✅ Works offline
- ⚠️ Limited to your computer

### Neo4j
- ✅ Network-accessible
- ✅ Advanced analytics
- ⚠️ Requires internet connection
- ⚠️ Slightly slower (network latency)

---

## Security & Privacy

### Local Storage
- Files stored on YOUR computer only
- No cloud transmission
- Fully private
- Protected by your OS permissions

### Neo4j
- Encrypted in transit (SSL)
- Stored in Neo4j Aura cloud
- Password protected
- Still private (only you can access)

---

## Summary

✅ **Your sessions ARE being saved** (locally)
✅ **All features work** (search, rename, delete, load)
✅ **No data loss** (even without Neo4j)
✅ **Automatic fallback** (seamless experience)

When Neo4j is fixed:
- New sessions will use Neo4j
- Old local sessions can be migrated
- Even better experience!

For now, enjoy the **fully functional local storage system**! 🎉

---

## Quick Reference

| Task | Command |
|------|---------|
| Test local storage | `python test_local_storage.py` |
| Test Neo4j | `python test_session_manager.py` |
| View saved sessions | Check `conversations/` folder |
| Backup | Copy `conversations/` folder |
| Run app | `python -m streamlit run app.py` |

---

**Questions?** Check the main `SESSION_MANAGEMENT_GUIDE.md` for advanced features!
