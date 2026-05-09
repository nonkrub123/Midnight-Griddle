"""
audiomanager.py
───────────────
Singleton audio manager. The clip registry lives inside the class
itself — edit SOUNDS and MUSIC below to add or change tracks.

Usage
─────
    from audiomanager import AudioManager
    audio = AudioManager()       # always returns the same instance

    audio.play_sound("click")
    audio.play_sound_loop("sizzle")
    audio.stop_sound("sizzle", fade_ms=300)

    audio.play_music("day")      # loops a single track forever
    audio.play_playlist()        # walks through MUSIC in order
    audio.next_music()
    audio.stop_music(fade_ms=500)
"""

from __future__ import annotations
import pygame


class AudioManager:

    # ── Registry — edit these to add/change clips ─────────────────────────────

    SOUNDS: dict[str, str] = {
        "bell":    "assets/sfx/bell.wav",
        "pick_pop":    "assets/sfx/pick_pop.wav",
        "place_pop":    "assets/sfx/place_pop.wav",
        "ghost_submit":    "assets/sfx/ghost_submit.wav",
        "sizzle_loop":    "assets/sfx/sizzle_loop.wav",
    }

    MUSIC: dict[str, str] = {
        # "spooky_fun":    "assets/bgm/the_mountain-spooky-fun-130051mp.3",
        # "spooky_fun":    "assets/bgm/the_mountain-spooky-scary-130009.mp3",
        # "spooky_fun":    "assets/bgm/viacheslavstarostin-halloween-spooky-music-411457.mp3",
    }

    # ── Singleton wiring ──────────────────────────────────────────────────────

    _instance: "AudioManager | None" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        # __new__ returns the existing instance on subsequent calls, but
        # Python still runs __init__ — guard against re-initializing.
        if self._initialized:
            return

        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        pygame.mixer.set_num_channels(32)   # ← was 8 by default

        self._sounds: dict[str, pygame.mixer.Sound]   = {}
        self._loops:  dict[str, pygame.mixer.Channel] = {}

        self._playlist: list[str] = list(self.MUSIC.keys())
        self._playlist_idx        = 0
        self._auto_advance        = False

        self.sfx_volume   = 0.7
        self.music_volume = 0.5

        self._preload_sounds()
        self._initialized = True

    def _preload_sounds(self):
        for name, path in self.SOUNDS.items():
            try:
                self._sounds[name] = pygame.mixer.Sound(path)
            except pygame.error as e:
                print(f"[audio] failed to load sound '{name}' ({path}): {e}")

    # ── Volume ────────────────────────────────────────────────────────────────

    def set_sfx_volume(self, v: float):
        self.sfx_volume = max(0.0, min(1.0, v))
        for snd in self._sounds.values():
            snd.set_volume(self.sfx_volume)

    def set_music_volume(self, v: float):
        self.music_volume = max(0.0, min(1.0, v))
        pygame.mixer.music.set_volume(self.music_volume)

    # ── SFX ───────────────────────────────────────────────────────────────────

    def play_sound(self, name: str):
        """One-shot SFX. Multiple calls overlap on free channels."""
        snd = self._sounds.get(name)
        if snd is None:
            return
        snd.set_volume(self.sfx_volume)
        snd.play()

    def play_sound_loop(self, name: str):
        """
        Loop a SFX. If already looping under this name, returns the existing
        channel without restarting. Otherwise returns the new channel.
        """
        existing = self._loops.get(name)
        if existing is not None and existing.get_busy():
            return existing

        snd = self._sounds.get(name)
        if snd is None:
            return None
        snd.set_volume(self.sfx_volume)
        ch = snd.play(loops=-1)
        self._loops[name] = ch
        return ch

    def stop_sound(self, name: str, fade_ms: int = 0):
        ch = self._loops.pop(name, None)
        if ch is None:
            return
        ch.fadeout(fade_ms) if fade_ms else ch.stop()

    def kill_all_sounds(self):
        """Kill every SFX channel and the music stream. Resets loop tracking."""
        pygame.mixer.stop()              # all SFX channels (one-shots + loops)
        pygame.mixer.music.stop()        # the music stream
        self._loops.clear()              # forget tracked loop channels
        self._auto_advance = False       # don't auto-resume the playlist

    def get_sound(self, name: str) -> pygame.mixer.Sound | None:
        return self._sounds.get(name)

    def pause_all(self):
        pygame.mixer.music.pause()
        pygame.mixer.pause()

    def resume_all(self):
        pygame.mixer.music.unpause()
        pygame.mixer.unpause()

    # ── Music ─────────────────────────────────────────────────────────────────

    def play_music(self, name: str | None = None, loop: bool = True):
        """
        Play a track by name. If no name is given, plays the current playlist
        position. loop=True repeats forever; loop=False plays once.
        """
        if name is None:
            if not self._playlist:
                return
            name = self._playlist[self._playlist_idx]

        path = self.MUSIC.get(name)
        if path is None:
            print(f"[audio] no music registered under '{name}'")
            return

        if name in self._playlist:
            self._playlist_idx = self._playlist.index(name)

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(loops=-1 if loop else 0)
        except pygame.error as e:
            print(f"[audio] failed to play music '{name}': {e}")

    def stop_music(self, fade_ms: int = 0):
        self._auto_advance = False
        if fade_ms:
            pygame.mixer.music.fadeout(fade_ms)
        else:
            pygame.mixer.music.stop()

    def next_music(self, loop: bool = False):
        """Advance the playlist by one and play that track."""
        if not self._playlist:
            return
        self._playlist_idx = (self._playlist_idx + 1) % len(self._playlist)
        self.play_music(self._playlist[self._playlist_idx], loop=loop)

    def play_playlist(self):
        """Start the playlist from the top with auto-advance enabled."""
        if not self._playlist:
            return
        self._playlist_idx = 0
        self._auto_advance = True
        self.play_music(self._playlist[0], loop=False)

    # ── Update (call once per frame for auto-advance) ─────────────────────────

    def update(self, dt=0):
        if self._auto_advance and not pygame.mixer.music.get_busy():
            self.next_music(loop=False)