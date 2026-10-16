# Claude Discord Presence

Shows your Claude Code token usage as your Discord activity:

```
Playing Token Counter
⚡ 𝗧𝗢𝗗𝗔𝗬 » 𝟭.𝟲𝗠 tokens
▱▱▱▱▱▱▱▱▱▱ 1% of best day
00:12 elapsed
```

Every 15 seconds it switches to the next slide: today, this week, all time, then model + streak.

It reads Claude Code's local logs in `%USERPROFILE%\.claude\projects`. Nothing is sent anywhere except to the Discord app on your own PC. It doesn't need npm packages, only Node.js.

> Only **Claude Code** usage is counted. Chats on claude.ai and in the Claude desktop Chat tab aren't stored locally, so this app can't see them.

## Setup (one time)

1. Go to https://discord.com/developers/applications and click **New Application**.
   Discord shows the name you pick after "Playing", so name it something like `Claude Code`.
2. On the **General Information** page, copy the **Application ID**.
3. Copy `config.example.json` to `config.json` and paste the ID into `clientId`.
4. (Optional) Add the animated picture. Upload `assets/claude-spark.gif` somewhere public, then put its direct `https://...gif` link in `largeImage`. Images uploaded under **Rich Presence → Art Assets** also work, but they don't animate. To redraw the GIF, run `python assets/make_gif.py`.

## Run

- `start.bat`: runs in a console window so you can see the log.
- `start-hidden.vbs`: runs in the background with no window. To start it with Windows, put a shortcut to it in your Startup folder (`Win+R` → `shell:startup`).
- `node index.js --print`: prints a full breakdown and exits, without connecting to Discord.

To stop the hidden version, end the `node.exe` process in Task Manager.

## Settings (`config.json`)

| Key | Default | Meaning |
| --- | --- | --- |
| `clientId` | — | Your Discord Application ID (required) |
| `refreshSeconds` | `15` | Seconds between slides (minimum 15, Discord's rate limit) |
| `countCacheReads` | `true` | Include cache-read tokens in totals. These are usually 95%+ of the total. Set to `false` for smaller, "real work" numbers |
| `activityType` | `0` | 0 Playing, 2 Listening to, 3 Watching, 5 Competing in |
| `showStatsInMemberList` | `true` | Show the stats line in the server member list instead of just the app name |
| `largeImage` | `""` | Image URL (a `.gif` animates) or art asset name |
| `largeImageText` | `""` | Hover text for the big image (defaults to today's total) |
| `smallImage` | `""` | Small corner badge image; its hover shows your streak |
| `buttons` | `[]` | Up to 2 buttons, e.g. `[{"label": "My GitHub", "url": "https://github.com/..."}]`. Only other people can see them |

Discord's **Activity Privacy** setting ("Share your detected activities with others") must be on for other people to see it.
