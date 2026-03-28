const { PDFDocument, rgb, StandardFonts, PDFName, PDFBool } = require('pdf-lib');
const fs = require('fs');
const path = require('path');

module.exports.config = {
  api: { bodyParser: { sizeLimit: '2mb' } }
};

const CHECKBOXES = [
  ['Special diet',    39.4, 423.9,  69.6, 424.1],
  ['Allergies',       39.4, 399.7,  69.1, 400.1],
  ['Self Admin',      39.9, 352.1,  69.7, 352.1],
  ['Chronic illness', 39.6, 288.1,  69.1, 288.2],
  ['Surgery',         39.5, 312.1,  69.2, 312.0],
];

async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).json({ error: 'Method not allowed' });

  try {
    let data = req.body;
    if (typeof data === 'string') {
      try { data = JSON.parse(data); } catch(e) { return res.status(400).json({ error: 'Invalid JSON' }); }
    }
    if (!data) return res.status(400).json({ error: 'Empty body' });

    // Find the blank PDF
    const possiblePaths = [
      path.join(process.cwd(), 'Permission_Blank.pdf'),
      path.join(process.cwd(), 'public', 'Permission_Blank.pdf'),
      path.join(__dirname, '..', 'Permission_Blank.pdf'),
    ];
    let pdfBytes = null;
    for (const p of possiblePaths) {
      try { if (fs.existsSync(p)) { pdfBytes = fs.readFileSync(p); break; } } catch(e) {}
    }
    if (!pdfBytes) return res.status(500).json({
      error: 'Permission_Blank.pdf not found',
      cwd: process.cwd(),
      tried: possiblePaths,
      ls: (() => { try { return fs.readdirSync(process.cwd()); } catch(e) { return []; } })()
    });

    const pdfDoc = await PDFDocument.load(pdfBytes);
    const form = pdfDoc.getForm();
    const page = pdfDoc.getPages()[0];

    // Set text fields — no updateAppearances, just set values
    // NeedAppearances tells the viewer to render them using its own fonts
    function setField(name, value) {
      try {
        if (value === null || value === undefined || value === '') return;
        form.getTextField(name).setText(String(value));
      } catch(e) {}
    }

    // Event details
    setField('Event',                                   data.evName);
    setField('Dates of event',                          data.evDates);
    setField('Event description',                       data.evDesc);
    setField('Ward',                                    data.evWard);
    setField('Stake',                                   data.evStake);
    setField('Event or activity leader',                'David Wheat (Bishop)');
    setField('Event or activity leaders phone number',  '210-601-2913');
    setField('Event or activity leaders email',         'creamof@gmail.com');

    // Participant
    setField('Participant',                             data.name);
    setField('Date of birth',                           data.dob);
    setField('Age',                                     data.age);
    setField('Telephone number',                        data.tel);
    setField('Address',                                 data.addr);
    setField('City',                                    data.city);
    setField('State or Province',                       data.state);
    setField('Emergency contact parent or guardian',    data.ec);
    setField('Primary phone_1',                         data.ec1);
    setField('Secondary phone_1',                       data.ec2);
    setField('List of Medications',                     data.meds);
    setField('diet explanation',                        data.diet);
    setField('Allergy explanation',                     data.allergy);
    setField('illness explanation',                     data.chronic);
    setField('If yes please explain_2',                 data.surgery);
    setField('Other limitations',                       data.limits);
    setField('Special needs',                           data.other);

    // Tell the viewer to render all field appearances from their values
    // This is the standard way — viewer uses its own fonts, works everywhere
    try {
      const acroForm = pdfDoc.catalog.lookup(PDFName.of('AcroForm'));
      if (acroForm) acroForm.set(PDFName.of('NeedAppearances'), PDFBool.True);
    } catch(e) {}

    // Draw X marks directly on the page for checkboxes
    const choices = {
      'Special diet':    data.diet_yn    || 'no',
      'Allergies':       data.allergy_yn || 'no',
      'Self Admin':      data.selfadmin  || 'yes',
      'Chronic illness': data.chronic_yn || 'no',
      'Surgery':         data.surgery_yn || 'no',
    };
    const s = 3.2;
    const black = rgb(0, 0, 0);
    for (const [name, yesX, yesY, noX, noY] of CHECKBOXES) {
      const cx = choices[name] === 'yes' ? yesX : noX;
      const cy = choices[name] === 'yes' ? yesY : noY;
      page.drawLine({ start: { x: cx-s, y: cy-s }, end: { x: cx+s, y: cy+s }, thickness: 1.5, color: black });
      page.drawLine({ start: { x: cx+s, y: cy-s }, end: { x: cx-s, y: cy+s }, thickness: 1.5, color: black });
    }

    // Save with useObjectStreams: false — produces a traditional xref table
    // compatible with ALL PDF viewers including old macOS Preview versions
    const result = await pdfDoc.save({ useObjectStreams: false });

    const safeName = (data.name || 'form').replace(/[^a-z0-9]/gi, '_');
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `attachment; filename="PermissionForm_${safeName}.pdf"`);
    res.send(Buffer.from(result));

  } catch(err) {
    console.error('PDF error:', err);
    res.status(500).json({ error: err.message, stack: err.stack });
  }
}

module.exports = handler;
