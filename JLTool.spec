# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
# pyinstaller JLTool.spec
datas = [('venv\Lib\site-packages\pykakasi\data', 'pykakasi\data'), ('tools', 'tools'),]
binaries = []
hiddenimports = []
for i in ['json', "tkinter", "langid", "pykakasi", "mutagen", "openai", "traceback"]:
    tmp_ret = collect_all(i)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['JLTool-kks.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
b = Analysis(
    ['JLTool-ds.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)
pyz1 = PYZ(b.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JLTool-kks',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['JLTool.ico'],
)
exe2 = EXE(
    pyz1,
    b.scripts,
    [],
    exclude_binaries=True,
    name='JLTool-ds',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['JLTool.ico'],
)
coll = COLLECT(
    exe,
    exe2,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JLTool',
)
