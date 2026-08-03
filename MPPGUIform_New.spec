# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['MPPGUIform_New.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'scapy.layers.all',
        'scapy.libs',
        'scapy.arch.windows',
        'scapy.sendrecv',
        'scapy.utils',
        'scapy.data',
        'scapy.consts',
        'scapy.error',
        'asn1crypto',
        'asn1crypto.x509'
        ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    uac_admin=False,
    name='C3_MPP_GUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,  
)
