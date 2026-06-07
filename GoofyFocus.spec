# GoofyFocus.spec
import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

datas = [
    ('assets', 'assets'),
    ('.env', '.'),
]
if os.path.exists('.secrets/client_secret.json'):
    datas.append(('.secrets/client_secret.json', '.secrets'))

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
        'pandas',
        'plotly',
        'plotly.graph_objects',
        'plotly.express',
        'plotly.subplots',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── Windows: directory build ──────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GoofyFocus',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='assets/icon.ico',
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
