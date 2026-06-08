# assets.py
import os
import sys
import random
import shutil
from PyQt6.QtCore import QStandardPaths, QCoreApplication

# 1. Initialize organization and app names on QCoreApplication
# to ensure QStandardPaths correctly creates subdirectories.
if not QCoreApplication.organizationName():
    QCoreApplication.setOrganizationName("GoofyFocus")
if not QCoreApplication.applicationName():
    QCoreApplication.setApplicationName("GoofyFocus")

def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

ASSETS_DIR = os.path.join(get_base_path(), "assets")

# Resolve correct, non-polluting user data directory
USER_DATA_DIR = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)

# Safe fallback check to prevent root folder pollution if it resolves to base Roaming
if USER_DATA_DIR.endswith("Roaming") or USER_DATA_DIR.endswith("AppData/Roaming") or USER_DATA_DIR.endswith("AppData\\Roaming"):
    USER_DATA_DIR = os.path.join(USER_DATA_DIR, "GoofyFocus")

USER_GIFS_DIR = os.path.join(USER_DATA_DIR, "gifs")
USER_SOUNDS_DIR = os.path.join(USER_DATA_DIR, "sounds")

# Ensure the new correct directories exist
os.makedirs(USER_GIFS_DIR, exist_ok=True)
os.makedirs(USER_SOUNDS_DIR, exist_ok=True)

# 2. Automated Migration to clean up polluted AppData/Roaming files
def _migrate_old_polluted_data():
    # Detect standard Roaming path
    roaming_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
    # If the default query returns the GoofyFocus nested path, get its parent's parent (which is Roaming)
    if "GoofyFocus" in roaming_dir:
        # traverse up to Roaming/AppData folder
        parts = os.path.split(roaming_dir)
        while parts[0] and "GoofyFocus" in parts[1]:
            roaming_dir = parts[0]
            parts = os.path.split(roaming_dir)
            
    # Validate roaming_dir is indeed the base AppData/Roaming path
    if not (roaming_dir.endswith("Roaming") or roaming_dir.endswith("AppData/Roaming") or roaming_dir.endswith("AppData\\Roaming")):
        return
        
    # Old paths
    old_sessions = os.path.join(roaming_dir, "sessions.json")
    old_session = os.path.join(roaming_dir, "session.json")
    old_gifs = os.path.join(roaming_dir, "gifs")
    old_sounds = os.path.join(roaming_dir, "sounds")
    
    # Target paths
    new_sessions = os.path.join(USER_DATA_DIR, "sessions.json")
    new_session = os.path.join(USER_DATA_DIR, "session.json")
    
    # 2a. Migrate sessions.json
    if os.path.exists(old_sessions) and not os.path.exists(new_sessions):
        try:
            shutil.move(old_sessions, new_sessions)
            print(f"[migration] Migrated sessions.json to {new_sessions}")
        except Exception as e:
            print(f"[migration] Failed migrating sessions.json: {e}")
            
    # 2b. Migrate session.json
    if os.path.exists(old_session) and not os.path.exists(new_session):
        try:
            shutil.move(old_session, new_session)
            print(f"[migration] Migrated session.json to {new_session}")
        except Exception as e:
            print(f"[migration] Failed migrating session.json: {e}")
            
    # 2c. Migrate gifs directory contents
    if os.path.isdir(old_gifs) and os.path.abspath(old_gifs) != os.path.abspath(USER_GIFS_DIR):
        try:
            for item in os.listdir(old_gifs):
                src_item = os.path.join(old_gifs, item)
                dst_item = os.path.join(USER_GIFS_DIR, item)
                if not os.path.exists(dst_item):
                    shutil.move(src_item, dst_item)
            # Remove old gifs folder if empty
            if not os.listdir(old_gifs):
                os.rmdir(old_gifs)
                print("[migration] Cleaned up old gifs folder")
        except Exception as e:
            print(f"[migration] Error migrating gifs: {e}")
            
    # 2d. Migrate sounds directory contents
    if os.path.isdir(old_sounds) and os.path.abspath(old_sounds) != os.path.abspath(USER_SOUNDS_DIR):
        try:
            for item in os.listdir(old_sounds):
                src_item = os.path.join(old_sounds, item)
                dst_item = os.path.join(USER_SOUNDS_DIR, item)
                if not os.path.exists(dst_item):
                    shutil.move(src_item, dst_item)
            # Remove old sounds folder if empty
            if not os.listdir(old_sounds):
                os.rmdir(old_sounds)
                print("[migration] Cleaned up old sounds folder")
        except Exception as e:
            print(f"[migration] Error migrating sounds: {e}")

    # 2e. Delete old empty sessions.json / session.json if they exist
    for f in [old_sessions, old_session]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

# Trigger migration once at import time
try:
    _migrate_old_polluted_data()
except Exception as e:
    print(f"[migration] Migration error: {e}")

class LocalAssetPicker:
    def __init__(self):
        self._gif_path:   str | None = None
        self._sound_path: str | None = None

    def start(self, is_pro: bool = False):
        self._gif_path   = self._pick_random_gif(is_pro)
        self._sound_path = self._pick_random_sound(is_pro)
        print(f"[assets] GIF  : {self._gif_path or 'none'}")
        print(f"[assets] Sound: {self._sound_path or 'none'}")

    def pop(self) -> tuple[str | None, str | None]:
        gif, sound = self._gif_path, self._sound_path
        self._gif_path = self._sound_path = None
        return gif, sound

    def _pick_random_gif(self, is_pro: bool = False) -> str | None:
        candidate_roots = [os.path.join(ASSETS_DIR, "gifs")]
        if is_pro and os.path.isdir(USER_GIFS_DIR):
            candidate_roots.append(USER_GIFS_DIR)

        all_gifs = []
        for root in candidate_roots:
            for dirpath, _, files in os.walk(root):
                all_gifs += [os.path.join(dirpath, f) for f in files if f.lower().endswith(".gif")]
        return random.choice(all_gifs) if all_gifs else None

    def _pick_random_sound(self, is_pro: bool = False) -> str | None:
        roots = [os.path.join(ASSETS_DIR, "sounds")]
        if is_pro and os.path.isdir(USER_SOUNDS_DIR):
            roots.append(USER_SOUNDS_DIR)
            
        sounds = []
        for root in roots:
            if os.path.isdir(root):
                sounds += [os.path.join(root, f) for f in os.listdir(root) if f.lower().endswith((".mp3", ".wav", ".ogg"))]
        return random.choice(sounds) if sounds else None