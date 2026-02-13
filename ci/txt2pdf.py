# ci/txt2pdf.py
# Скрипт для CI: конвертирует текстовый отчёт (TXT) в PDF
# Запуск:
#   python ci/txt2pdf.py input.txt output.pdf

import sys
from fpdf import FPDF  # библиотека для создания PDF (пакет fpdf2)

# Берём аргументы командной строки:
# sys.argv[1] — путь к входному TXT
# sys.argv[2] — путь к выходному PDF
inp, out = sys.argv[1], sys.argv[2]

# Создаём PDF-документ
pdf = FPDF()
pdf.add_page()  # добавляем страницу

# Выбираем шрифт (моноширинный Courier, размер 10)
# Для ASCII/латиницы обычно подходит. Для кириллицы может понадобиться TTF-шрифт.
pdf.set_font("Courier", size=10)

# Открываем входной файл (если встретятся “странные” символы — заменяем их, чтобы не падало)
with open(inp, "r", encoding="utf-8", errors="replace") as f:
    for line in f:
        # Убираем перенос строки в конце
        text = line.rstrip("\n")
        # multi_cell печатает строку и сам переносит на новую строку,
        # а также переносит длинный текст по ширине страницы
        pdf.multi_cell(0, 5, text)

# Сохраняем PDF в указанный файл
pdf.output(out)
