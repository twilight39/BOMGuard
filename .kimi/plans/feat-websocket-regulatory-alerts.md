# Plan: WebSocket Regulatory Alerts

## Goal
Deliver real-time regulatory change notifications to connected clients.

## Scope
- `backend/bomguard/websocket.py`
- `backend/bomguard/ingestion/pipeline.py` (emit on change)
- Frontend hook / toast component

## Tasks
1. [ ] **Connection manager**: Finish `websocket.py` to track active connections by user/session.
2. [ ] **Broadcast helper**: `broadcast_regulatory_alert(regulation_id, change_summary)` sends JSON to all connected clients.
3. [ ] **Hook ingestion pipeline**: After `ingestion/pipeline.py` detects a SHA-256 hash change and inserts into `regulatory_changes`, call broadcast.
4. [ ] **Frontend hook**: `useRegulatoryAlerts()` that connects to `ws://host/ws/regulations`, handles reconnect, and exposes a toast queue.
5. [ ] **Toast UI**: shadcn/ui toast showing regulation name, changed substance count, and link to feed.
6. [ ] **Auth scoping**: Only send alerts to authenticated admins (optional); public users get generic announcements.
7. [ ] **Tests**: Backend pytest for `websocket.py`; frontend can be manual for now.

## Dependencies
- None (can be built in parallel)

## Outcome
Users see a live toast when new regulatory data is ingested, without polling.
