# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules


hiddenimports = collect_submodules("keyring.backends") + [
    "bs4",
    "soupsieve",
    "openpyxl",
    "reportlab",
    "googleapiclient",
    "googleapiclient.discovery",
    "google.oauth2.service_account",
    "google_auth_httplib2",
    "httplib2",
    "keyring",
    "jaraco.classes",
    "jaraco.context",
    "jaraco.functools",
]

a = Analysis(
    ["app_v46.py"],
    pathex=[],
    binaries=[],
    datas=[
        ("assets/seo_ai_studio_icon.ico", "assets"),
        ("assets/seo_ai_studio_icon.png", "assets"),
    ],
    hiddenimports=hiddenimports,
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
    name="SEO_AI_Studio_V46",
    icon="assets/seo_ai_studio_icon.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
