# Installation

Here are the [Red](https://github.com/Cog-Creators/Red-DiscordBot) commands to add this repository (use your bot's prefix in place of `[p]`):
```
[p]load downloader
[p]repo add CBD-Cogs https://gitlab.com/CrunchBangDev/cbd-cogs
```

You may be prompted to respond with "I agree" after that.


# Cogs

You can install individual cogs like this:
```
[p]cog install CBD-Cogs [cog]
```

Just replace `[cog]` with the name of the cog you want to install.

## Bio

Add information to your player bio and lookup information others have shared.

Bio is basically a key/value store for each user where the allowed keys are determined by server admins.

### Commands

| Command     | Description |
| ----------- | ----------- |
| `bio`       | Display and modify your bio or view someone else's bio |
| `biofields` | List the available bio fields |
| `biosearch` | Find field values across all users |

## Scrub

Applies a set of rules to remove undesireable elements from hyperlinks such as campaign tracking tokens.

Since bots can't edit people's messages, it reposts the cleaned links.

### Commands

| Command       | Description |
| ------------- | ----------- |
| `scrubupdate` | Update Scrub with the latest rules |

### Credits

Thanks to [Walter](https://github.com/walterl) for making [Uroute](https://github.com/walterl/uroute) from which this borrows heavily.

Thanks to [Kevin](https://gitlab.com/KevinRoebert) for the [ClearURLs](https://gitlab.com/KevinRoebert/ClearUrls) rule set without which this cog wouldn't work.

## Tube

Posts in a channel every time a new video is added to a YouTube channel.

### Commands

| Command       | Description |
| ------------- | ----------- |
| `list`        | List current subscriptions |
| `subscribe`   | Subscribe a Discord channel to a YouTube channel |
| `unsubscribe` | Unsubscribe a Discord channel from a YouTube channel |
| `update`      | Update feeds and post new videos |

### Credits

Thanks to [Sinbad](https://github.com/mikeshardmind) for the [RSS cog](https://github.com/mikeshardmind/SinbadCogs/tree/v3/rss) I based this on.