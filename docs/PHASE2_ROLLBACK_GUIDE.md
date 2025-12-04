# Phase 2 Rollback Guide

## 🚨 Quick Rollback (If Results Are Bad)

### Option 1: Environment Variable (Fastest - No Code Changes)

Add to your `.env` file:
```env
RAG_OPTIMIZED_LIMITS_ENABLED=false
```

Then restart the backend. This will immediately revert to original limits:
- Podcast: 20 chunks
- Others: 10 chunks

### Option 2: Git Rollback (Complete Revert)

```bash
# Switch back to main branch
git checkout main

# Or if you want to keep the branch but revert the changes
git checkout phase2-optimize-limits
git revert HEAD
```

### Option 3: Manual Code Revert

In `backend/app/core/config.py`, change:
```python
RAG_OPTIMIZED_LIMITS_ENABLED: bool = os.getenv("RAG_OPTIMIZED_LIMITS_ENABLED", "false").lower() == "true"
```

Change `"true"` to `"false"` to disable by default.

---

## 📊 What Changed

### Original Limits (Before Phase 2)
- **Podcast**: 20 chunks
- **QA/General**: 10 chunks
- **Speech/Doc/PPT**: 10 chunks

### Phase 2 Optimized Limits
- **Podcast**: 10 chunks (50% reduction)
- **Speech/Doc/PPT/MP4**: 8 chunks (20% reduction)
- **QA/General**: 6 chunks (40% reduction)

### Expected Impact
- **Faster responses**: 40-50% reduction in context size
- **Lower costs**: 40-50% reduction in token usage
- **Same/better quality**: Focused, relevant chunks

---

## 🧪 Testing Checklist

Test these scenarios to verify Phase 2 is working:

### 1. QA (General Questions)
- [ ] Ask a general question
- [ ] Check logs: Should see "6 chunks" for QA
- [ ] Verify answer quality is same or better

### 2. Podcast Generation
- [ ] Create a podcast
- [ ] Check logs: Should see "10 chunks" for podcast
- [ ] Verify podcast is comprehensive and complete

### 3. Speech Generation
- [ ] Create a speech
- [ ] Check logs: Should see "8 chunks" for speech
- [ ] Verify speech covers all key points

### 4. Document Generation
- [ ] Generate a document
- [ ] Check logs: Should see "8 chunks" for doc
- [ ] Verify document is complete

### 5. Presentation Generation
- [ ] Generate a presentation
- [ ] Check logs: Should see "8 chunks" for ppt
- [ ] Verify presentation covers all topics

---

## 📈 Monitoring

### What to Watch For

**Good Signs:**
- ✅ Faster response times
- ✅ Same or better answer quality
- ✅ Lower token usage in logs
- ✅ No complaints about missing information

**Bad Signs (Rollback if you see these):**
- ❌ Answers missing important information
- ❌ Podcasts/speeches seem incomplete
- ❌ Users complaining about quality
- ❌ Significant increase in "I don't know" responses

### Log Monitoring

Look for these log messages:
```
[Phase 2 Optimized] Retrieved 6/6 document chunks for question: '...'
[Phase 2 Optimized] Retrieved 10/10 document chunks for action request: '...'
```

If you see quality issues, check:
1. Are we getting enough chunks? (Should match the limit)
2. Are the chunks relevant? (Check similarity scores)
3. Is the answer complete? (Compare with original)

---

## 🔄 Rollback Decision Matrix

| Issue | Severity | Action |
|-------|----------|--------|
| Missing critical information | High | **Rollback immediately** |
| Slightly incomplete answers | Medium | Monitor for 24 hours |
| Faster but same quality | Low | Keep Phase 2 |
| Faster and better quality | Low | Keep Phase 2 |

---

## 📝 Rollback Steps (Detailed)

### Step 1: Disable Phase 2 (Environment Variable)

1. Open `backend/.env`
2. Add: `RAG_OPTIMIZED_LIMITS_ENABLED=false`
3. Restart backend: `uvicorn main:app --reload`
4. Test: Should see "Using original RAG limits" in logs

### Step 2: Verify Rollback

Check logs for:
```
Using original RAG limits - podcast: 20 chunks
Using original RAG limits - QA: 10 chunks
```

### Step 3: Test Quality

Run the same tests as before and verify:
- Answers are complete
- No missing information
- Quality is back to original

---

## 🎯 Success Criteria

Phase 2 is successful if:
1. ✅ Response times are 40-50% faster
2. ✅ Token usage is 40-50% lower
3. ✅ Answer quality is same or better
4. ✅ No user complaints about missing information
5. ✅ All test scenarios pass

If all criteria are met, Phase 2 is a success! 🎉

---

## 📞 Support

If you need help with rollback or have questions:
1. Check logs: `backend/logs/` or console output
2. Review this guide
3. Check `docs/RAG_IMPROVEMENT_ANALYSIS.md` for technical details

