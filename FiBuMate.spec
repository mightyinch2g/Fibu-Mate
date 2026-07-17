# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\python\\config', 'config'), ('C:\\python\\bin\\tools', 'bin\\tools'), ('C:\\python\\bin\\Imgs', 'bin\\Imgs')]
binaries = []
hiddenimports = ['bs4', 'charset_normalizer', 'comtypes', 'cryptography', 'customtkinter', 'dateutil', 'docx', 'et_xmlfile', 'fitz', 'lxml', 'matplotlib', 'matplotlib.backends.backend_tkagg', 'numpy', 'openpyxl', 'openpyxl.styles', 'openpyxl.utils', 'packaging', 'pandas', 'pdfminer', 'pdfminer.high_level', 'pdfplumber', 'PIL', 'PIL.Image', 'PIL.ImageDraw', 'PIL.ImageEnhance', 'PIL.ImageFont', 'PIL.ImageOps', 'PIL.ImageTk', 'pptx', 'pypdf', 'PyPDF2', 'pythoncom', 'pywintypes', 'reportlab', 'reportlab.pdfbase', 'reportlab.pdfgen', 'reportlab.platypus', 'requests', 'tkcalendar', 'tkinter', 'tkinter.colorchooser', 'tkinter.constants', 'tkinter.filedialog', 'tkinter.font', 'tkinter.messagebox', 'tkinter.scrolledtext', 'tkinter.simpledialog', 'tkinter.ttk', 'win32com', 'win32com.client', 'xlrd', 'xlsxwriter']
datas += collect_data_files('customtkinter')
datas += collect_data_files('docx')
datas += collect_data_files('matplotlib')
datas += collect_data_files('openpyxl')
datas += collect_data_files('pandas')
datas += collect_data_files('pptx')
datas += collect_data_files('reportlab')
datas += collect_data_files('tkcalendar')
tmp_ret = collect_all('bs4')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('charset_normalizer')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('cryptography')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('customtkinter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('docx')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('et_xmlfile')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('fitz')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('lxml')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('openpyxl')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pdfminer')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pdfplumber')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PIL')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pptx')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('pypdf')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('PyPDF2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('reportlab')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('requests')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('tkcalendar')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('xlrd')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('xlsxwriter')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:\\python\\Fibu_mate.py'],
    pathex=['C:\\python\\bin', 'C:\\python\\bin\\tools'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['adbc_driver_manager', 'boto3', 'botocore', 'comtypes.test', 'django', 'django.db', 'django.db.backends', 'docutils', 'flask', 'gi', 'IPython', 'jedi', 'jupyter', 'llvmlite', 'matplotlib.backends.backend_cairo', 'matplotlib.backends.backend_gtk3', 'matplotlib.backends.backend_gtk3agg', 'matplotlib.backends.backend_gtk3cairo', 'matplotlib.backends.backend_gtk4', 'matplotlib.backends.backend_gtk4agg', 'matplotlib.backends.backend_gtk4cairo', 'matplotlib.backends.backend_macosx', 'matplotlib.backends.backend_nbagg', 'matplotlib.backends.backend_qt', 'matplotlib.backends.backend_qt5', 'matplotlib.backends.backend_qt5agg', 'matplotlib.backends.backend_qt5cairo', 'matplotlib.backends.backend_qtagg', 'matplotlib.backends.backend_qtcairo', 'matplotlib.backends.backend_webagg', 'matplotlib.backends.backend_wx', 'matplotlib.backends.backend_wxagg', 'matplotlib.backends.backend_wxcairo', 'matplotlib.sphinxext', 'matplotlib.testing', 'matplotlib.tests', 'notebook', 'numba', 'parso', 'py', 'pyarrow', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'pytest', 'scipy', 'sphinx', 'sqlalchemy'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FiBuMate',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FiBuMate',
)
