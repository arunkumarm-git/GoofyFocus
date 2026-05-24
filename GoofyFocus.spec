# GoofyFocus.spec
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = [
    ('assets', 'assets'),
    ('.env', '.'),
]
if os.path.exists('client_secret.json'):
    datas.append(('client_secret.json', '.'))

a = Analysis(
    ['app.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
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
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

if sys.platform == 'win32':
    # ── Windows: single-file EXE ─────────────────────────────────────
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        [],
        name='GoofyFocus',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=[],
        console=False,
        icon='assets/icon.ico',
        onefile=True,
    )
else:
    # ── macOS: .app bundle ───────────────────────────────────────────
    # onefile=False is required — COLLECT+BUNDLE need folder mode
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,   # <-- required for COLLECT to work
        name='GoofyFocus',
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
        icon='assets/icon.icns',
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name='GoofyFocus',
    )

    app = BUNDLE(
        coll,
        name='GoofyFocus.app',
        icon='assets/icon.icns',
        bundle_identifier='com.arun.goofyfocus',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion':            '1',
            'NSHighResolutionCapable':    True,
            'LSMinimumSystemVersion':     '10.14',
            'NSPrincipalClass':           'NSApplication',
            'NSAppleScriptEnabled':       False,
        },
    )
