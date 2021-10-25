# TODO

## Main

- [ ] Custom Bot Class
  - [ ] Bot Checks
  - [x] Multiple Owners
  - [x] Get prefix function (sync or async)
  - [ ] Regex prefix?

- [ ] Plugins
  - [x] Support Prefix Commands
  - [x] Support Slash Commands
  - [x] Support Message Commands
  - [x] Support User Commands
  - [x] Support Listeners
  - [ ] Plugin Unload Hook
  - [ ] Plugin Check
  - [ ] Plugin error handler

- [ ] Commands
  - [x] Base Command
  - [x] Base Application Command (needs creation methods)
  - [ ] Prefix Commands
    - [x] Invocation
    - [ ] Parsing
    - [ ] Groups & subcommands
  - [ ] Slash Commands
    - [x] Option Types
    - [x] Channel Types
    - [ ] Groups & subcommands
    - [ ] ~~Autocomplete~~ (blocked)
  - [ ] ~~Message Commands~~ (blocked)
  - [ ] ~~User Commands~~ (blocked)
  - [ ] Per-Command Error Handler
    - [x] Prefix commands
    - [ ] Slash commands
    - [ ] ~~Message commands~~ (blocked)
    - [ ] ~~User commands~~ (blocked)
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
  - [ ] Custom Checks
  - [ ] Check Exempt?

- [ ] Context
  - [x] Base Class
  - [x] Prefix Context
  - [x] Slash Context
  - [ ] ~~Message Context~~ (blocked)
  - [ ] ~~User Context~~ (blocked)

- [ ] Converters (Reuse?)
  - [ ] User Converter
  - [ ] Member Converter
  - [ ] Text Channel Converter
  - [ ] Guild Voice Channel Converter
  - [ ] Category Converter
  - [ ] Role Converter
  - [ ] Emoji Converter
  - [ ] Guild Converter
  - [ ] Message Converter
  - [ ] Invite Converter
  - [ ] Colo(u)r Converter
  - [ ] Timestamp Converter

- [ ] Special Args
  - [ ] Greedy
  - [ ] Consume Rest

- [ ] Cooldowns (Reuse?)

- [x] Events
  - [x] *Command Completion Event
  - [x] *Command Invocation Event
  - [x] *Command Error Event

- [ ] Errors (Reuse?)

- [ ] Parsing
  - [ ] Standard Parser
  - [ ] CLI Parser
  - [ ] Custom Parsing

- [ ] Help Command

- [ ] Paginators (Reuse?)

- [ ] Navigators (Reuse?)

- [ ] Utils (Reuse?)
  - [ ] get
  - [ ] find
  - [x] permissions_in
  - [x] permissions_for

## Other

- [ ] Paginated/Navigated Help Command
- [ ] Embed Help Command
- [ ] Default Ephemeral Flags
- [ ] Reinvoke on edits
- [ ] Default allowed mentions
- [ ] Broadcast typing on command invocation
