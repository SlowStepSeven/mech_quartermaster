# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        # tcss lands at _MEIPASS root so _css_path() finds it as os.path.join(_MEIPASS, 'mq.tcss')
        ('src/mech_quartermaster/mq.tcss', '.'),
    ],
    hiddenimports=[
        # Our package — all modules are dynamically imported via __import__ in main_hub.py
        'mech_quartermaster',
        'mech_quartermaster.app',
        'mech_quartermaster.game',
        'mech_quartermaster.mech',
        'mech_quartermaster.missions',
        'mech_quartermaster.data',
        'mech_quartermaster.ui',
        'mech_quartermaster.campaigns',
        'mech_quartermaster.campaigns.base',
        'mech_quartermaster.campaigns.iron_lance',
        'mech_quartermaster.screens',
        'mech_quartermaster.screens.campaign_select',
        'mech_quartermaster.screens.setup_game',
        'mech_quartermaster.screens.main_hub',
        'mech_quartermaster.screens.inspect',
        'mech_quartermaster.screens.advance',
        'mech_quartermaster.screens.repair',
        'mech_quartermaster.screens.parts',
        'mech_quartermaster.screens.order',
        'mech_quartermaster.screens.market',
        'mech_quartermaster.screens.deploy',
        'mech_quartermaster.screens.end_screens',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mech-quartermaster',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
