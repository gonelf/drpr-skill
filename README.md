# drpr Claude Code Plugin

Publish files to [drpr.host](https://drpr.host) directly from Claude Code.

## Install

Open Claude Code and run:

```
/plugin marketplace add drpr-host/claude-plugin
/plugin install drpr@drpr
```

Then just say **"publish this"** or **"give me a shareable link"** and Claude handles the rest — including opening your browser to log in on the first run.

## What it does

1. Checks if you're logged in
2. If not, opens drpr.host in your browser and waits for you to log in
3. Uploads your file with your account
4. Returns a live URL

## Usage

```
/drpr:drpr publish /path/to/file.html
```

Or just ask naturally:
> "Publish this page to drpr"
> "Give me a shareable link for this file"

## Commands

| Tool | Description |
|------|-------------|
| `drpr_login` | Authenticate via browser |
| `drpr_upload` | Upload a file and get a URL |
| `drpr_status` | Check auth status |
| `drpr_logout` | Log out |
