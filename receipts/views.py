from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.db.models import Q
from django.urls import reverse
from django.core.paginator import Paginator
from .models import OfficialReceipt
from .forms import OfficialReceiptForm
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Image, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from reportlab.lib.units import inch
import os
from django.conf import settings
import logging
from reportlab.pdfgen import canvas
from num2words import num2words

# Set up logging
logger = logging.getLogger(__name__)

def get_filtered_receipts(query):
    queryset = OfficialReceipt.objects.all()
    if query:
        queryset = queryset.filter(
            Q(or_number__icontains=query) |
            Q(payor_name__icontains=query) |
            Q(reference_number__icontains=query)
        )
    return queryset

class WatermarkedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        self.pagesize = kwargs.get('pagesize', letter)
        super().__init__(*args, **kwargs)
        self.static_dir = settings.STATICFILES_DIRS[0]
        self.logo_path = os.path.join(self.static_dir, 'images', 'dost-logo-transparent.png')
        self.stamp_path = os.path.join(self.static_dir, 'images', 'cancelled-stamp.png')
        self.is_deleted = kwargs.get('is_deleted', False)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        """Apply watermark behind page content before final output."""
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_watermark()
            if self.is_deleted:
                self.draw_stamp()
            super().showPage()
        super().save()

    def draw_watermark(self):
        if os.path.exists(self.logo_path):
            page_width, page_height = self.pagesize
            logo_width = 550
            logo_height = 550
            x = (page_width - logo_width) / 2
            y = (page_height - logo_height) / 2

            self.saveState()
            self.setFillAlpha(0.5)
            self.drawImage(
                self.logo_path,
                x, y,
                width=logo_width,
                height=logo_height,
                preserveAspectRatio=True,
                mask='auto'
            )
            self.restoreState()
    
    def draw_stamp(self):
        if os.path.exists(self.stamp_path):
            page_width, page_height = self.pagesize
            stamp_width = 200  # Adjust size as needed
            stamp_height = 100  # Adjust size as needed
            x = (page_width - stamp_width) / 2
            y = (page_height - stamp_height) / 2

            self.saveState()
            self.setFillAlpha(0.7)  # Adjust opacity for stamp
            self.drawImage(
                self.stamp_path,
                x, y,
                width=stamp_width,
                height=stamp_height,
                preserveAspectRatio=True,
                mask='auto'
            )
            self.restoreState()

@login_required
def receipt_list(request):
    query = request.GET.get('q', '')
    receipts = get_filtered_receipts(query)
    paginator = Paginator(receipts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'receipts': page_obj,
        'query': query,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        html = render_to_string('receipts/receipt_table.html', context, request=request)
        return JsonResponse({'table_html': html})
    else:
        return render(request, 'receipts/receipt_list.html', context)

@login_required
def receipt_create(request):
    query = request.GET.get('q', '') or request.POST.get('q', '')
    page = request.GET.get('page') or request.POST.get('page')

    if request.method == 'POST':
        form = OfficialReceiptForm(request.POST)
        if form.is_valid():
            receipt = form.save()
            return JsonResponse({ 'success': True, 'receipt_id': receipt.pk })
        else:
            return JsonResponse({
                'success': False,
                'html': render_to_string('receipts/receipt_form_modal.html', {
                    'form': form,
                    'query': query,
                    'page': page,
                    'form_title': 'Create Receipt',
                    'action_url': request.path
                }, request=request)
            })

    form = OfficialReceiptForm()
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'receipts/receipt_form_modal.html', {
            'form': form,
            'query': query,
            'page': page,
            'form_title': 'Create Receipt',
            'action_url': request.path
        })

    return render(request, 'receipts/receipt_form.html', {
        'form': form,
        'query': query,
        'page': page,
    })

@login_required
def receipt_edit(request, pk):
    receipt = get_object_or_404(OfficialReceipt, pk=pk, is_deleted=False)
    query = request.GET.get('q', '') or request.POST.get('q', '')
    page = request.GET.get('page') or request.POST.get('page')

    if request.method == 'POST':
        form = OfficialReceiptForm(request.POST, instance=receipt)  
        if form.is_valid():
            receipt = form.save()
            return JsonResponse({ 'success': True, 'receipt_id': receipt.pk })
        else:
            return JsonResponse({
                'success': False,
                'html': render_to_string('receipts/receipt_form_modal.html', {
                    'form': form,
                    'query': query,
                    'page': page,
                    'form_title': 'Edit Receipt',
                    'action_url': request.path  
                }, request=request)
            })

    form = OfficialReceiptForm(instance=receipt)
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'receipts/receipt_form_modal.html', {
            'form': form,
            'query': query,
            'page': page,
            'form_title': 'Edit Receipt',
            'action_url': request.path  
        })

    return render(request, 'receipts/receipt_form.html', {
        'form': form,
        'query': query,
        'page': page,
    })

@login_required
def receipt_delete(request, pk):
    receipt = get_object_or_404(OfficialReceipt, pk=pk)
    query = request.GET.get('q', '') or request.POST.get('q', '')
    page_number = request.GET.get('page', 1)

    if request.method == 'POST':
        receipt.is_deleted = True
        receipt.save()

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})
        
        return redirect(f"{reverse('receipt_list')}?q={query}&page={page_number}")

     # AJAX GET request: Return modal HTML
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        receipts = get_filtered_receipts(query)
        paginator = Paginator(receipts, 10)
        page_obj = paginator.get_page(page_number)

        return render(request, 'receipts/receipt_confirm_delete.html', {
            'receipt': receipt,
            'receipts': page_obj,
            'query': query,
        })

    return redirect('receipt_list')

@login_required
def receipt_pdf(request, pk):
    receipt = get_object_or_404(OfficialReceipt, pk=pk)
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    elements = []
    styles = getSampleStyleSheet()

    # Styles
    header_style = styles['Heading1']
    header_style.fontSize = 12
    header_style.textColor = colors.black
    header_style.alignment = 1  # Center
    header_style.leading = 16
    normal_style = styles['Normal']
    normal_style.fontSize = 11
    normal_style.leading = 16

    underline_bold = styles['Normal'].clone('UnderlineBold')
    underline_bold.fontSize = 11
    underline_bold.leading = 14
    underline_bold.fontName = 'Helvetica-Bold'
    underline_bold.underline = True

    left_align_bold = underline_bold.clone('LeftBold')
    left_align_bold.alignment = 0

    small_centered = styles['Normal'].clone('SmallCentered')
    small_centered.fontSize = 10
    small_centered.alignment = 1
    small_centered.leading = 10

    footnote_style = styles['Normal'].clone('Footnote')
    footnote_style.fontSize = 8
    footnote_style.alignment = 1
    footnote_style.fontName = 'Helvetica-Oblique'

    # Header
    # Load and center logo above header
    static_dir = settings.STATICFILES_DIRS[0]
    logo_path = os.path.join(static_dir, 'images', 'dost-logo.png')
    logo = Image(logo_path, width=0.6*inch, height=0.6*inch)
    logo.hAlign = 'CENTER'

    # Add logo
    elements.append(logo)

    # Header text centered below logo
    elements.append(Spacer(1, 4))  # Slight space between logo and header
    elements.append(Paragraph("Electronic Official Receipt (eOR)", header_style))
    elements.append(Paragraph("Department of Science and Technology", header_style))
    elements.append(Paragraph("Regional Office 02", header_style))
    elements.append(Paragraph("Regional Government Center, Carig Sur, Tuguegarao City, Cagayan", small_centered))
    elements.append(Spacer(1, 16))

    reference_code = receipt.reference_number or ""

    date_str = f"Date and Time:<br/><b><u>{receipt.date_time.strftime('%m/%d/%Y %I:%M:%S %p')}</u></b>"
    or_str = f"OR Number: <br/><b><u>{receipt.or_number}</u></b>"
    payor_str = f"Payor: <br/><b><u>{receipt.payor_name}</u></b>"
    ref_str = f"Reference Code:<br/><b><u>{reference_code}</u></b>"

    date_or_table = Table([[Paragraph(date_str, normal_style), Paragraph(or_str, normal_style)]],
                          colWidths=[3.5 * inch, 2.5 * inch])
    date_or_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    elements.append(date_or_table)
    elements.append(Spacer(1, 2))

    new_row = Table([[Paragraph(payor_str, normal_style), Paragraph(ref_str, normal_style)]],
                          colWidths=[3.5 * inch, 2.5 * inch])
    new_row.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
    ]))
    elements.append(new_row)
    elements.append(Spacer(1, 20))
    
    # amount_total = round(receipt.amount + receipt.vat + receipt.service_charge, 2) # Future use
    amount_total = round(receipt.amount, 2)

    pesos = int(amount_total)
    centavos = int(round((amount_total - pesos) * 100))

    pesos_words = num2words(pesos, lang='en').replace(",", "").replace(" and ", " ")
    centavos_words = num2words(centavos, lang='en').replace(",", "") if centavos > 0 else "zero"

    if centavos > 0:
        amount_in_words = f"{pesos_words} pesos and {centavos_words} centavos"
    else:
        amount_in_words = f"{pesos_words} pesos only"

    amount_in_words = amount_in_words.upper()

    # Table Data
    data = [
        ["Nature of Collection", "Amount"],
        [f"{receipt.purpose}", f"{receipt.amount:,.2f}"],
        ["", ""],
        # ["VAT (12%)", f"{receipt.vat:,.2f}"], # Future use
        # ["Service Charge", f"{receipt.service_charge:,.2f}"], # Future use
        ["", ""],
        ["", ""],
        ["", ""],
        ["", ""],
        ["", ""],
        ["", ""],
        # ["Net Amount", f"PHP {(receipt.amount + receipt.vat + receipt.service_charge):,.2f}"], # Future use
        ["Net Amount", f"PHP {(receipt.amount):,.2f}"],
        [Paragraph(f"Amount in Words: <b>{amount_in_words}</b>", normal_style)]
    ]

    table = Table(data, colWidths=[3.5 * inch, 2.5 * inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#003366")),  
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),            
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, 9), 'RIGHT'),  
        ('ALIGN', (0, 9), (0, 9), 'RIGHT'),                      
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),              
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'), 
        ('FONTNAME', (0, 9), (0, 9), 'Helvetica-Bold'),
        ('FONTNAME', (1, 9), (1, 9), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.red),
        ('TEXTCOLOR', (0, 9), (0, 9), colors.black),                 
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('LINEBEFORE', (1, 0), (1, -1), 1, colors.black),             
        ('LINEAFTER', (0, 0), (0, -1), 1, colors.black),              
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),    
        ('LINEABOVE', (0, 9), (-1,9), 1, colors.black),
        ('LINEABOVE', (0, 10), (-1,10), 1, colors.black),
        ('SPAN', (0, 10), (-1, 10)), 
        ('ALIGN', (0, 10), (-1, 10), 'LEFT'),          
        ('BOX', (0, 0), (-1, -1), 1, colors.black),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 24))

    # Footer
    payment_channel = receipt.payment_channel or ""
    mode_of_payment = receipt.mode_of_payment or ""

    paychan_str = f"Payment Channel: <br/><b><u>{payment_channel}</u></b>"
    modpay_str = f"Mode of Payment: <br/><b><u>{mode_of_payment}</u></b>"

    pay_row = Table([[Paragraph(paychan_str, normal_style), Paragraph(modpay_str, normal_style)]],
                          colWidths=[3.5 * inch, 2.5 * inch])
    pay_row.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP')
    ]))
    elements.append(pay_row)
    elements.append(Spacer(1, 24))

    elements.append(Paragraph("------------------------------------------------------------------------------------------------------------------------------------------------------------------", footnote_style))
    elements.append(Paragraph("This is a computer-generated receipt. No signature required.", footnote_style))
    elements.append(Paragraph("------------------------------------------------------------------------------------------------------------------------------------------------------------------", footnote_style))
    elements.append(Spacer(1, 12))

    # Build
    doc.build(elements, canvasmaker=lambda *args, **kw: WatermarkedCanvas(*args, is_deleted=receipt.is_deleted, **kw))
    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{receipt.or_number}.pdf"'
    response.write(pdf)
    return response

@login_required
def profile_view(request):
    return render(request, 'receipts/profile.html', {'user': request.user})