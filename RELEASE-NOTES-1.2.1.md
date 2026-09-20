Bug-fix release. Everything here matters to dictee users running the overlay.

### The overlay no longer stays on screen after `stop`

Told to stop, it only stopped drawing. Its layer surface stayed mapped,
invisible, holding the exclusive keyboard grab that `--on-escape` asks for.
You were left with a window in the way after every dictation, and only a
`kill` got rid of it (dictee#34).

`stop` now hides the window, `start` shows it again.

### The overlay no longer swallows clicks

GTK builds a fresh `wl_surface` on every map and does not carry the input
shape over, so the empty input region is now re-asserted every time the
overlay comes back. Without it, clicks landing on the overlay area were
captured instead of reaching the window underneath.

### No more unreachable instances

- A second instance refuses to start instead of overwriting the single PID
  file and orphaning the first one.
- `animation-speech-ctl` checks that the PID it read is really ours before
  signalling it. A PID file left behind by a `kill -9` points at a number the
  kernel is free to hand out to anything else, and `quit` would have killed a
  stranger's process.

### Install

```
sudo dpkg -i animation-speech_1.2.1_all.deb              # Debian, Ubuntu
sudo dnf install animation-speech-1.2.1-1.noarch.rpm     # Fedora, openSUSE
```
