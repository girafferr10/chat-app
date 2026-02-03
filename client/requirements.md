## Packages
(none needed)

## Notes
WebSocket connects to window.location.protocol === 'https:' ? 'wss://' : 'ws://' + window.location.host + '/ws'
Messages are received via WebSocket (join, chat, user_list, history)
