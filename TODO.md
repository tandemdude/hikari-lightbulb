# TODO

## Main

- [x] Custom Bot Class
  - [x] Bot Checks
  - [x] Multiple Owners
  - [x] Get prefix function (sync or async)
  - [ ] Regex prefix?

- [x] Plugins
  - [x] Support Prefix Commands
  - [x] Support Slash Commands
  - [x] Support Message Commands
  - [x] Support User Commands
  - [x] Support Listeners
  - [x] Plugin Unload Hook
  - [x] Plugin Check
  - [x] Plugin error handler

- [ ] Extensions
  - [ ] Load
  - [ ] Unload
  - [ ] Reload

- [ ] Commands
  - [x] Base Command
  - [x] Base Application Command (needs creation methods)
  - [ ] Prefix Commands
    - [x] Invocation
    - [x] Parsing
    - [ ] Groups & subcommands
  - [ ] Slash Commands
    - [x] Option Types
    - [x] Channel Types
    - [ ] Groups & subcommands
    - [ ] ~~Autocomplete~~ (blocked)
  - [ ] ~~Message Commands~~ (blocked)
  - [ ] ~~User Commands~~ (blocked)
  - [x] Per-Command Error Handler
    - [x] Prefix commands
    - [x] Slash commands
    - [x] ~~Message commands~~ (blocked)
    - [x] ~~User commands~~ (blocked)
  - [ ] Auto-managing of Application Commands
  
- [ ] Checks (Reuse?)
  - [x] DM Only
  - [x] Guild Only
  - [x] Human Only
  - [x] Bot Only
  - [x] Webhook Only
  - [x] Owner Only
  - [ ] Has Roles
  - [ ] (Bot) Has Guild Permissions
  - [ ] (Bot) Has Role Permissions
  - [ ] (Bot) Has Channel Permissions
  - [ ] Has Attachment
  - [x] Custom Checks
  - [ ] Check Exempt?

- [ ] Context
  - [x] Base Class
  - [x] Prefix Context
  - [x] Slash Context
  - [ ] ~~Message Context~~ (blocked)
  - [ ] ~~User Context~~ (blocked)

- [x] Converters
  - [x] Base Converter
  - [x] User Converter
  - [x] Member Converter
  - [x] Guild Channel Converter
  - [x] Guild Voice Channel Converter
  - [x] Category Converter
  - [x] Guild Text Channel Converter
  - [x] Role Converter
  - [x] Emoji Converter
  - [x] Guild Converter
  - [x] Message Converter
  - [x] Invite Converter
  - [x] Colo(u)r Converter
  - [x] Timestamp Converter

- [ ] Special Converter Support for Slash Commands?

- [x] Special Args
  - [x] Greedy
  - [x] Consume Rest

- [ ] Cooldowns (Reuse?)

- [x] Events
  - [x] *Command Completion Event
  - [x] *Command Invocation Event
  - [x] *Command Error Event

- [ ] Errors (Reuse?)

- [ ] Parsing
  - [x] Standard Parser
  - [ ] CLI Parser
  - [x] Custom Parsing

- [ ] Help Command

- [x] Paginators (Reuse?)

- [x] Navigators (Reuse?)

- [x] Utils (Reuse?)
  - [x] get
  - [x] find
  - [x] permissions_in
  - [x] permissions_for

## Other

- [ ] Paginated/Navigated Help Command
- [ ] Embed Help Command
- [ ] Default Ephemeral Flags
- [ ] Reinvoke on edits
- [ ] Default allowed mentions
- [ ] Broadcast typing on command invocation
