# Mic Controller

This folder is the Stream Deck plugin for `com.shay.miccontroller.sdPlugin`.

## Files

- `manifest.json` - plugin metadata and action registration
- `plugin.html` - Stream Deck plugin entry point
- `main.js` - WebSocket and action handling scaffold

- `propertyinspector/` - image settings for muted and unmuted states

## Behavior

- Receives status changes through `/miccontroller/events` using SSE.
- Pressing a key calls `/miccontroller/toggle` and immediately updates the icon.
- `/miccontroller/events` confirms the icon with Server-Sent Events.
- The plugin does not use a periodic REST polling loop for status updates.
- The property inspector lets the user choose separate custom images for the
  muted and unmuted states.
- The server implementation is in
  `server/com.shay.miccontroller.sdPlugin/micController.py`.
