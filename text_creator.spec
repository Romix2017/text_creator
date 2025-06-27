# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['text_dictator.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Add PyQt6 plugins
a.binaries += Tree('C:\\Users\\rvk-pc\\AppData\\Local\\Programs\\Python\\Python311\\Lib\\site-packages\\PyQt6\\Qt6\\plugins', 'PyQt6/Qt6/plugins')

# Add the icon if you have one
# a.datas += [('icon.ico', 'icon.ico', 'DATA')]

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='TextDictator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False to hide console window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add path to your .ico file if you have one
)
