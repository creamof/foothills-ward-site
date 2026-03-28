from http.server import BaseHTTPRequestHandler
import json, os, io
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, create_string_object

CHECKBOXES = [
    ('Special diet',    39.4, 423.9,  69.6, 424.1),
    ('Allergies',       39.4, 399.7,  69.1, 400.1),
    ('Self Admin',      39.9, 352.1,  69.7, 352.1),
    ('Chronic illness', 39.6, 288.1,  69.1, 288.2),
    ('Surgery',         39.5, 312.1,  69.2, 312.0),
]

def get_pdf_path():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in [
        os.path.join(base, 'Permission_Blank.pdf'),
        os.path.join(base, 'public', 'Permission_Blank.pdf'),
        os.path.join(os.getcwd(), 'Permission_Blank.pdf'),
    ]:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f'Permission_Blank.pdf not found. base={base} cwd={os.getcwd()}')

def fill_pdf(data):
    pdf_path = get_pdf_path()

    # Step 1: fill text fields using pypdf
    r = PdfReader(pdf_path)
    w = PdfWriter()
    w.append(r)

    TEXT_FIELDS = {
        'Event':                                    data.get('evName', ''),
        'Dates of event':                           data.get('evDates', ''),
        'Event description':                        data.get('evDesc', ''),
        'Ward':                                     data.get('evWard', ''),
        'Stake':                                    data.get('evStake', ''),
        'Event or activity leader':                 data.get('evLeader', 'David Wheat'),
        'Event or activity leaders phone number':   data.get('evPhone', '210-601-2913'),
        'Event or activity leaders email':          data.get('evEmail', 'creamof@gmail.com'),
        'Participant':                              data.get('name', ''),
        'Date of birth':                            data.get('dob', ''),
        'Age':                                      data.get('age', ''),
        'Telephone number':                         data.get('tel', ''),
        'Address':                                  data.get('addr', ''),
        'City':                                     data.get('city', ''),
        'State or Province':                        data.get('state', ''),
        'Emergency contact parent or guardian':     data.get('ec', ''),
        'Primary phone_1':                          data.get('ec1', ''),
        'Secondary phone_1':                        data.get('ec2', ''),
        'List of Medications':                      data.get('meds', ''),
        'diet explanation':                         data.get('diet', ''),
        'Allergy explanation':                      data.get('allergy', ''),
        'illness explanation':                      data.get('chronic', ''),
        'If yes please explain_2':                  data.get('surgery', ''),
        'Other limitations':                        data.get('limits', ''),
        'Special needs':                            data.get('other', ''),
    }
    w.update_page_form_field_values(w.pages[0], TEXT_FIELDS, auto_regenerate=False)

    # Set NeedAppearances so viewer renders field values
    if '/AcroForm' in w._root_object:
        w._root_object['/AcroForm'].update({
            NameObject('/NeedAppearances'): create_string_object('true')
        })

    # Write filled PDF to buffer
    buf1 = io.BytesIO()
    w.write(buf1)
    buf1.seek(0)

    # Step 2: draw X marks as overlay using reportlab
    choices = {
        'Special diet':    data.get('diet_yn', 'no'),
        'Allergies':       data.get('allergy_yn', 'no'),
        'Self Admin':      data.get('selfadmin', 'yes'),
        'Chronic illness': data.get('chronic_yn', 'no'),
        'Surgery':         data.get('surgery_yn', 'no'),
    }
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(612, 792))
    c.setStrokeColor(black)
    c.setLineWidth(1.3)
    s = 3.2
    for (name, yesX, yesY, noX, noY) in CHECKBOXES:
        cx = yesX if choices.get(name) == 'yes' else noX
        cy = yesY if choices.get(name) == 'yes' else noY
        c.line(cx-s, cy-s, cx+s, cy+s)
        c.line(cx+s, cy-s, cx-s, cy+s)
    c.save()
    packet.seek(0)

    # Step 3: merge overlay onto filled PDF
    overlay_reader = PdfReader(packet)
    filled_reader = PdfReader(buf1)
    final_writer = PdfWriter()
    final_writer.append(filled_reader)
    final_writer.pages[0].merge_page(overlay_reader.pages[0])

    out = io.BytesIO()
    final_writer.write(out)
    return out.getvalue()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            pdf_bytes = fill_pdf(data)
            name = (data.get('name', 'form') or 'form').replace(' ', '_')
            self.send_response(200)
            self.send_header('Content-Type', 'application/pdf')
            self.send_header('Content-Disposition',
                f'attachment; filename="PermissionForm_{name}.pdf"')
            self.send_header('Content-Length', str(len(pdf_bytes)))
            self.end_headers()
            self.wfile.write(pdf_bytes)
        except Exception as e:
            import traceback
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'error': str(e),
                'trace': traceback.format_exc()
            }).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
