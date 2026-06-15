cd /d "C:\python"

python -m pip install --upgrade pip setuptools wheel

python -m pip install --upgrade ^
  pyinstaller ^
  pillow ^
  pandas ^
  openpyxl ^
  xlrd ^
  PyPDF2 ^
  pypdf ^
  pymupdf ^
  python-docx ^
  python-pptx ^
  reportlab ^
  matplotlib ^
  numpy ^
  requests ^
  beautifulsoup4 ^
  lxml ^
  tkcalendar ^
  customtkinter ^
  cryptography ^
  python-dateutil ^
  packaging ^
  charset-normalizer

if exist "C:\python\build" rmdir /s /q "C:\python\build"
if exist "C:\python\dist\FiBuMate" rmdir /s /q "C:\python\dist\FiBuMate"
if exist "C:\python\FiBuMate.spec" del /q "C:\python\FiBuMate.spec"

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --onedir ^
  --name "FiBuMate" ^
  --paths "C:\python\bin" ^
  --paths "C:\python\bin\tools" ^
  --collect-all PIL ^
  --collect-all pandas ^
  --collect-all openpyxl ^
  --collect-all xlrd ^
  --collect-all PyPDF2 ^
  --collect-all pypdf ^
  --collect-all fitz ^
  --collect-all docx ^
  --collect-all pptx ^
  --collect-all reportlab ^
  --collect-all matplotlib ^
  --collect-all numpy ^
  --collect-all requests ^
  --collect-all bs4 ^
  --collect-all lxml ^
  --collect-all tkcalendar ^
  --collect-all customtkinter ^
  --collect-all cryptography ^
  --collect-all dateutil ^
  --collect-all packaging ^
  --collect-all charset_normalizer ^
  --hidden-import PIL ^
  --hidden-import PIL.Image ^
  --hidden-import PIL.ImageTk ^
  --hidden-import pandas ^
  --hidden-import openpyxl ^
  --hidden-import xlrd ^
  --hidden-import PyPDF2 ^
  --hidden-import pypdf ^
  --hidden-import fitz ^
  --hidden-import docx ^
  --hidden-import pptx ^
  --hidden-import reportlab ^
  --hidden-import matplotlib ^
  --hidden-import numpy ^
  --hidden-import requests ^
  --hidden-import bs4 ^
  --hidden-import lxml ^
  --hidden-import tkcalendar ^
  --hidden-import customtkinter ^
  --hidden-import cryptography ^
  --hidden-import dateutil ^
  --hidden-import packaging ^
  --hidden-import charset_normalizer ^
  --add-data "C:\python\bin\tools;bin\tools" ^
  --add-data "C:\python\bin\Imgs;bin\Imgs" ^
  "C:\python\Fibu_mate.py"
