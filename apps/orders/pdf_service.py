"""
Сервис для генерации PDF отчетов и предпросмотров
"""
import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfgen import canvas
from django.utils.text import slugify
import logging

logger = logging.getLogger(__name__)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


# Register a TTF font that supports Cyrillic to avoid missing glyphs (squares)
_DEFAULT_TTF = None
_BOLD_TTF = None
_FONT_NAME_REG = 'SND-Regular'
_FONT_NAME_BOLD = 'SND-Bold'

# Try common Windows fonts and DejaVu
_font_candidates = [
    r'C:\Windows\Fonts\arial.ttf',
    r'C:\Windows\Fonts\tahoma.ttf',
    r'C:\Windows\Fonts\calibri.ttf',
    r'C:\Windows\Fonts\times.ttf',
    r'C:\Windows\Fonts\arialuni.ttf',
    r'C:\Windows\Fonts\arialbd.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
]

def _register_fonts():
    global _DEFAULT_TTF, _BOLD_TTF
    regular = None
    bold = None
    # find regular and bold fonts
    for p in _font_candidates:
        if os.path.exists(p):
            low = os.path.basename(p).lower()
            if 'bold' in low or 'bd' in low or ('arialbd' in low):
                # consider as bold
                if not bold:
                    bold = p
            else:
                if not regular:
                    regular = p
    # Fallback specific pairs
    if regular and bold:
        try:
            pdfmetrics.registerFont(TTFont(_FONT_NAME_REG, regular))
            pdfmetrics.registerFont(TTFont(_FONT_NAME_BOLD, bold))
            _DEFAULT_TTF = _FONT_NAME_REG
            _BOLD_TTF = _FONT_NAME_BOLD
            logger.info(f"PDF fonts registered: regular={regular}, bold={bold}")
            return
        except Exception:
            pass
    # Try to detect arial and arialbd specifically
    arial = r'C:\Windows\Fonts\arial.ttf'
    arialbd = r'C:\Windows\Fonts\arialbd.ttf'
    if os.path.exists(arial):
        try:
            pdfmetrics.registerFont(TTFont(_FONT_NAME_REG, arial))
            _DEFAULT_TTF = _FONT_NAME_REG
            logger.info(f"PDF font registered: regular={arial}")
        except Exception:
            _DEFAULT_TTF = None
    if os.path.exists(arialbd):
        try:
            pdfmetrics.registerFont(TTFont(_FONT_NAME_BOLD, arialbd))
            _BOLD_TTF = _FONT_NAME_BOLD
            logger.info(f"PDF font registered: bold={arialbd}")
        except Exception:
            _BOLD_TTF = None
    # If still none, try DejaVu
    dejavu = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    dejavu_b = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    if not _DEFAULT_TTF and os.path.exists(dejavu):
        try:
            pdfmetrics.registerFont(TTFont(_FONT_NAME_REG, dejavu))
            _DEFAULT_TTF = _FONT_NAME_REG
            logger.info(f"PDF font registered: regular={dejavu}")
        except Exception:
            _DEFAULT_TTF = None
    if not _BOLD_TTF and os.path.exists(dejavu_b):
        try:
            pdfmetrics.registerFont(TTFont(_FONT_NAME_BOLD, dejavu_b))
            _BOLD_TTF = _FONT_NAME_BOLD
            logger.info(f"PDF font registered: bold={dejavu_b}")
        except Exception:
            _BOLD_TTF = None


_register_fonts()

if not _DEFAULT_TTF:
    # as a last resort, use Helvetica (may not support Cyrillic)
    _DEFAULT_TTF = 'Helvetica'
if not _BOLD_TTF:
    _BOLD_TTF = 'Helvetica-Bold'


class OrderPDFGenerator:
    """Генератор PDF для заказов"""
    def __init__(self, order=None):
        self.order = order
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontName=_BOLD_TTF,
            fontSize=24,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=20,
            alignment=1  # Center
        )
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontName=_BOLD_TTF,
            fontSize=14,
            textColor=colors.HexColor('#2a5a90'),
            spaceAfter=10,
            spaceBefore=10
        )
    
    def generate_order_pdf(self, order):
        """Генерирует PDF для заказа"""
        self.order = order
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        elements = []
        
        # Заголовок
        title = Paragraph(f"Заказ #{order.order_id}", self.title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Use Paragraph for textual cells so ReportLab uses the registered TTF
        table_text_style = ParagraphStyle(
            'TableText',
            parent=self.styles['Normal'],
            fontName=_DEFAULT_TTF,
            fontSize=10,
            leading=12,
        )

        info_data = [
            [Paragraph('Номер заказа:', table_text_style), Paragraph(str(order.order_id), table_text_style)],
            [Paragraph('Дата:', table_text_style), Paragraph(order.order_date.strftime('%d.%m.%Y %H:%M'), table_text_style)],
            [Paragraph('Статус:', table_text_style), Paragraph(str(order.status).upper(), table_text_style)],
            [Paragraph('Сумма:', table_text_style), Paragraph(f'{order.total_amount} ₽', table_text_style)],
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f0f8')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), _BOLD_TTF),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Информация о клиенте
        elements.append(Paragraph("Информация о клиенте", self.heading_style))
        customer_data = [
            [Paragraph('ФИО:', table_text_style), Paragraph(f"{order.customer.first_name} {order.customer.last_name}", table_text_style)],
            [Paragraph('Email:', table_text_style), Paragraph(order.customer.email or 'N/A', table_text_style)],
            [Paragraph('Телефон:', table_text_style), Paragraph(order.customer.phone or 'Не указан', table_text_style)],
        ]
        customer_table = Table(customer_data, colWidths=[2*inch, 3*inch])
        customer_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f8f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), _BOLD_TTF),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))
        elements.append(customer_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Адрес доставки
        if order.shipping_address:
            elements.append(Paragraph("Адрес доставки", self.heading_style))
            address_text = order.shipping_address.full_address or f"{order.shipping_address.city}, {order.shipping_address.street}"
            address_data = [
                [Paragraph('Адрес:', table_text_style), Paragraph(address_text, table_text_style)],
            ]
            address_table = Table(address_data, colWidths=[2*inch, 3*inch])
            address_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f8f0f0')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), _BOLD_TTF),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ]))
            elements.append(address_table)
            elements.append(Spacer(1, 0.2*inch))
        
        # Товары в заказе
        elements.append(Paragraph("Товары в заказе", self.heading_style))
        items_data = [[Paragraph('№', table_text_style), Paragraph('Товар', table_text_style), Paragraph('Кол-во', table_text_style), Paragraph('Цена', table_text_style), Paragraph('Сумма', table_text_style)]]

        for idx, item in enumerate(order.order_items.all(), 1):
            item_sum = float(item.quantity) * float(item.price_at_purchase)
            product_name = getattr(item.product, 'product_name', '') or ''
            items_data.append([
                Paragraph(str(idx), table_text_style),
                Paragraph(product_name[:60], table_text_style),
                Paragraph(str(item.quantity), table_text_style),
                Paragraph(f'{item.price_at_purchase} ₽', table_text_style),
                Paragraph(f'{item_sum:.2f} ₽', table_text_style)
            ])
        
        items_table = Table(items_data, colWidths=[0.4*inch, 2.5*inch, 0.8*inch, 1*inch, 1*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), _BOLD_TTF),
            ('FONTNAME', (0, 1), (-1, -1), _DEFAULT_TTF),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f8f8')]),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Итог
        total_data = [
            ['', '', '', 'Итого:', f'{order.total_amount} ₽'],
        ]
        total_table = Table(total_data, colWidths=[0.4*inch, 2.5*inch, 0.8*inch, 1*inch, 1*inch])
        total_table.setStyle(TableStyle([
            ('BACKGROUND', (3, 0), (-1, -1), colors.HexColor('#1a5490')),
            ('TEXTCOLOR', (3, 0), (-1, -1), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (3, 0), (-1, -1), _BOLD_TTF),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(total_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Подпись
        elements.append(Paragraph(
            "Благодарим Вас за покупку! Спасибо, что выбрали SND Shop.",
            ParagraphStyle(
                'Footer',
                parent=self.styles['Normal'],
                fontName=_DEFAULT_TTF,
                fontSize=10,
                alignment=1,
                textColor=colors.grey
            )
        ))
        
        doc.build(elements)
        buffer.seek(0)
        return buffer


class ReportPDFGenerator:
    """Генератор PDF для отчетов"""
    
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontName=_BOLD_TTF,
            fontSize=20,
            textColor=colors.HexColor('#1a5490'),
            spaceAfter=20,
            alignment=1
        )
        self.heading_style = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontName=_BOLD_TTF,
            fontSize=12,
            textColor=colors.HexColor('#2a5a90'),
            spaceAfter=10,
            spaceBefore=10
        )
    
    def generate_sales_report_pdf(self, start_date, end_date, data):
        """Генерирует PDF для отчета о продажах"""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        elements = []
        
        # Заголовок
        title = Paragraph("ОТЧЕТ ПО ПРОДАЖАМ", self.title_style)
        elements.append(title)

        # Период и временная метка
        now = datetime.now()
        period_text = f"Период: последний месяц | Дата: {now.strftime('%d.%m.%Y %H:%M')}"
        elements.append(Paragraph(period_text, self.heading_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Таблица данных — поддерживаем два варианта: per-product rows или аггрегированные
        if isinstance(data, list) and data:
            table_text_style = ParagraphStyle(
                'ReportTableText',
                parent=self.styles['Normal'],
                fontName=_DEFAULT_TTF,
                fontSize=9,
                leading=11,
            )
            header_style = ParagraphStyle(
                'ReportHeader',
                parent=self.styles['Normal'],
                fontName=_BOLD_TTF,
                fontSize=10,
                leading=12,
                alignment=1,
            )

            # If rows contain product_name -> render product-level table
            first = data[0]
            if 'product_name' in first or 'sku' in first:
                report_data = [[
                    Paragraph('ID', header_style),
                    Paragraph('Название Товара', header_style),
                    Paragraph('SKU', header_style),
                    Paragraph('Категория', header_style),
                    Paragraph('Кол-во', header_style),
                    Paragraph('Выручка (RUB)', header_style),
                ]]

                total_revenue = 0
                total_quantity = 0
                for idx, row in enumerate(data, 1):
                    total_revenue += float(row.get('revenue') or 0)
                    total_quantity += int(row.get('quantity') or 0)
                    report_data.append([
                        Paragraph(str(idx), table_text_style),
                        Paragraph(str(row.get('product_name') or ''), table_text_style),
                        Paragraph(str(row.get('sku') or ''), table_text_style),
                        Paragraph(str(row.get('category') or ''), table_text_style),
                        Paragraph(str(row.get('quantity') or 0), table_text_style),
                        Paragraph(f"{float(row.get('revenue') or 0):.2f}", table_text_style),
                    ])

                # итоговая строка
                report_data.append([
                    Paragraph('', table_text_style),
                    Paragraph('', table_text_style),
                    Paragraph('', table_text_style),
                    Paragraph('ИТОГО:', header_style),
                    Paragraph(str(total_quantity), table_text_style),
                    Paragraph(f"{total_revenue:.2f}", table_text_style),
                ])

                table = Table(report_data, colWidths=[0.4*inch, 3*inch, 1.2*inch, 1.2*inch, 0.8*inch, 1.2*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), _BOLD_TTF),
                    ('FONTNAME', (0, 1), (-1, -1), _DEFAULT_TTF),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f8f8')]),
                ]))
                elements.append(table)

                # Summary
                elements.append(Spacer(1, 0.2*inch))
                summary_style = ParagraphStyle(
                    'Summary',
                    parent=self.styles['Normal'],
                    fontSize=9,
                    textColor=colors.HexColor('#1a1a1a'),
                    alignment=0,
                    spaceAfter=6,
                    fontName=_DEFAULT_TTF
                )
                elements.append(Paragraph(f'<b>Всего товаров продано:</b> {total_quantity} шт.', summary_style))
                elements.append(Paragraph(f'<b>Общая выручка:</b> {total_revenue:.2f} RUB', summary_style))
                elements.append(Paragraph(f'<b>Период анализа:</b> с {start_date.strftime("%d.%m.%Y")} по {end_date.strftime("%d.%m.%Y")}', summary_style))

            else:
                # fallback: category/brand aggregated table (existing behavior)
                report_data = [[
                    Paragraph('Категория', header_style),
                    Paragraph('Бренд', header_style),
                    Paragraph('Заказов', header_style),
                    Paragraph('Товаров', header_style),
                    Paragraph('Доход', header_style),
                    Paragraph('Средний чек', header_style),
                ]]

                for row in data:
                    report_data.append([
                        Paragraph(str(row.get('category', '')), table_text_style),
                        Paragraph(str(row.get('brand', '')), table_text_style),
                        Paragraph(str(row.get('orders', 0)), table_text_style),
                        Paragraph(str(row.get('items', 0)), table_text_style),
                        Paragraph(f"{row.get('revenue', 0)} ₽", table_text_style),
                        Paragraph(f"{row.get('avg_order', 0)} ₽", table_text_style),
                    ])

                table = Table(report_data, colWidths=[1.5*inch, 1.2*inch, 0.8*inch, 0.8*inch, 1*inch, 1*inch])
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), _BOLD_TTF),
                    ('FONTNAME', (0, 1), (-1, -1), _DEFAULT_TTF),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f8f8')]),
                ]))
                elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
    
    def generate_inventory_report_pdf(self, inventory_data):
        """Генерирует PDF для отчета об инвентаре"""
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.5*inch,
            leftMargin=0.5*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        elements = []
        
        # Заголовок
        title = Paragraph("Отчет об инвентаре", self.title_style)
        elements.append(title)
        elements.append(Spacer(1, 0.2*inch))
        
        # Таблица данных
        if inventory_data:
            inv_data = [['SKU', 'Товар', 'Категория', 'Кол-во', 'Статус']]
            for item in inventory_data:
                status = 'Нормально' if item.get('quantity', 0) > 20 else 'Мало' if item.get('quantity', 0) > 0 else 'Нет'
                inv_data.append([
                    item.get('sku', ''),
                    item.get('name', '')[:25],
                    item.get('category', ''),
                    str(item.get('quantity', 0)),
                    status
                ])
            
            table = Table(inv_data, colWidths=[1*inch, 2*inch, 1.5*inch, 0.8*inch, 1*inch])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a5490')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), _BOLD_TTF),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f0f8f8')]),
            ]))
            elements.append(table)
        
        doc.build(elements)
        buffer.seek(0)
        return buffer
