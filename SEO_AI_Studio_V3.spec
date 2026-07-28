# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['app_v3.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets/seo_ai_studio_icon.ico', 'assets'),
        ('assets/seo_ai_studio_icon.png', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SEO_AI_Studio_V3',
    icon='assets/seo_ai_studio_icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
