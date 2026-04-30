# ScreenBreak.spec
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets', 'assets'),        # bundles entire assets/ folder
        ('.env', '.'),               # bundles your .env file
        ('client_secret.json', '.'), # bundles Google OAuth secret
    ],
    hiddenimports=[
        'PyQt6.QtMultimedia',
        'PyQt6.QtMultimediaWidgets',
        'google_auth_oauthlib',
        'google_auth_oauthlib.flow',
        'google.auth.transport.requests',
        'google.oauth2.credentials',
        'supabase',
        'dotenv',
        'PIL',
        'PIL.Image',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Windows / Linux: single-file EXE ─────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ScreenBreak',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,           # No terminal window (GUI app)
    icon='assets/icon.ico',  # Windows uses .ico
    onefile=True,            # Single .exe
)

# ── macOS: .app bundle ────────────────────────────────────────────────────────
# COLLECT is REQUIRED before BUNDLE. Without it, PyInstaller has no folder-mode
# representation to wrap into the .app structure → dist/ScreenBreak.app is never created.
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ScreenBreak',      # The folder name inside dist/
)

app = BUNDLE(
    coll,                    # <-- must reference coll, not exe directly
    name='ScreenBreak.app',
    icon='assets/icon.icns', # macOS uses .icns — run: sips -s format icns assets/icon.png --out assets/icon.icns
    bundle_identifier='com.arun.screenbreak',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion':            '1',
        'NSHighResolutionCapable':    True,
        'LSMinimumSystemVersion':     '10.14',
        'NSPrincipalClass':           'NSApplication',
        'NSAppleScriptEnabled':       False,
    },
)
