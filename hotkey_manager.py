from typing import Callable, Dict, Optional
from pynput import keyboard

class HotkeyManager:
    def __init__(self):
        self._bindings: Dict[tuple, Callable] = {}
        self._pressed_keys = set()
        self._listener: Optional[keyboard.Listener] = None
        self._enabled = True

    def start(self) -> None:
        if self._listener is None:
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
            )
            self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def bind(self, hotkey: tuple, callback: Callable) -> None:
        self._bindings[hotkey] = callback

    def unbind(self, hotkey: tuple) -> None:
        self._bindings.pop(hotkey, None)

    def clear(self) -> None:
        self._bindings.clear()

    def _normalize_key(self, key) -> Optional[str]:
        if isinstance(key, keyboard.KeyCode):
            if key.char:
                return key.char.lower()
            return f"<{key.vk}>"
        elif isinstance(key, keyboard.Key):
            return key.name
        return None

    def _on_press(self, key) -> None:
        if not self._enabled:
            return
        normalized = self._normalize_key(key)
        if normalized is None:
            return
        self._pressed_keys.add(normalized)
        self._check_bindings()

    def _on_release(self, key) -> None:
        normalized = self._normalize_key(key)
        if normalized is None:
            return
        self._pressed_keys.discard(normalized)

    def _check_bindings(self) -> None:
        for hotkey, callback in list(self._bindings.items()):
            if set(hotkey).issubset(self._pressed_keys):
                try:
                    callback()
                except Exception as e:
                    print(f"Ошибка в callback хоткея {hotkey}: {e}")

    @staticmethod
    def parse_hotkey_string(hotkey_str: str) -> tuple:
        if not hotkey_str:
            return tuple()
        parts = [p.strip().lower() for p in hotkey_str.split("+")]
        return tuple(parts)