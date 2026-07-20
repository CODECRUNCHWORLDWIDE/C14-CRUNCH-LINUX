# C14 · Crunch Linux — Brand Guide

> **Voice:** dry, terminal-honest, allergic to TUI marketing-speak. The voice of a sysadmin's morning coffee.
> **Feel:** monospace-heavy, blinking-cursor minimal, paper-tape utility.

Extends the family brand. C14-specific overrides only.

---

## Identity

- **Full name:** Crunch Linux
- **Program code:** C14
- **Full title in copy:** *C14 · Crunch Linux*
- **Tagline (short):** Live in the terminal.
- **Tagline (long):** A free, open-source eight-week Linux track — terminal fluency, systemd services, hardened SSH, and a server you actually run.
- **Canonical URL:** `codecrunchglobal.vercel.app/course-c14-linux`
- **License:** GPL-3.0

---

## Where C14 diverges from the family palette

Inherits Ink/Parchment/Gold. Adds **Bash Yellow** as a single restrained accent — directly inspired by the historical Unix yellow caution color:

| Role | Name | Hex | Use |
|------|------|-----|-----|
| Accent | Bash Yellow | `#FACC15` | The C14 mark, "use with care" callouts, root prompts |
| Accent deep | Bash Yellow deep | `#A16207` | Hover states, eyebrows |
| Accent soft | Bash Yellow soft | `#FEF08A` | Subtle highlight on shell-snippet rows |

```css
:root {
  --bash-yellow:       #FACC15;
  --bash-yellow-deep:  #A16207;
  --bash-yellow-soft:  #FEF08A;
}
```

### Typography

EB Garamond display, Lora body. **Mono is dominant in C14 chrome** — buttons, table cells, even the prose "command" notation. JetBrains Mono. Where C8 uses mono only for code, C14 uses mono everywhere a sysadmin would be reading at a terminal.

---

## Recurring page elements

### The prompt-aware code block

Distinguish user prompt from root prompt visually:

```
user@host:~$ ls -la /etc
```

vs

```
root@host:~# systemctl restart sshd
```

Rules:

- `$` for user prompts, `#` for root prompts.
- The prompt itself is colored Bash Yellow Deep; the command is Ink.
- A root prompt **must** be preceded by a one-line warning if the command is irreversible.

### The "kernel-style log line"

Sysadmins read log lines all day. The visual element looks like:

```
[2026-05-13 14:00:01.142]  systemd[1]: Started example.service.
[2026-05-13 14:00:01.358]  example.service[1247]: listening on :8080
```

Always mono. Faint Rule-colored timestamps; Ink-colored body. Never colorize the message — that's a tool decision, and the curriculum should look like raw `journalctl` output.

---

## Voice rules

- **No "easy" or "just."** "Just edit /etc/ssh/sshd_config and restart" — the word "just" hides a lot of opportunity to lock yourself out. Don't say it.
- **Always show the rollback path.** Every page that teaches a destructive command teaches its inverse.
- **Cite the distro.** "Debian / Ubuntu uses systemd-resolved" — not "Linux uses." Distros differ; admit it.
- **Use full paths.** `/etc/ssh/sshd_config` — not "the SSH config file." Beginners need the path.
- **No "haxor" jokes.** The terminal is a workplace. Treat it like one.

---

## Course page conventions

The course page (`course-c14-linux.html`, future) uses an *inverted* parchment-on-Ink hero, mimicking a terminal. The cursor is a steady (not blinking — accessibility) Bash Yellow rectangle. The 8-week ladder is rendered as a `tree`-output style listing.

---

*GPL-3.0. Fork freely.*
