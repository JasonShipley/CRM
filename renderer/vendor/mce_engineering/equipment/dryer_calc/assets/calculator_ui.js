/* MCE rotary dryer calculator UI. All numbers come from the workbook's formulas via xlcalc (MODEL). */
(function () {
  'use strict';
  var wb = new xlcalc.Workbook(MODEL);
  var S = {};
  MODEL.sheets.forEach(function (n, i) { S[n] = i; });
  var SI = S['Inputs'], SC = S['Calc'];
  var fmt = xlcalc.format, isErr = xlcalc.isErr;
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var STORE = 'mce-dryer-entries-v1';

  function nm(n) { return wb.name(n); }
  function calcRow(n) { var d = MODEL.names[n]; return d && d[0] === SC ? d[1] : null; }
  function si(n) {  // metric value + unit from the Calc sheet's SI columns
    var r = calcRow(n); if (!r) return '';
    var v = wb.cell(SC, r, 5), u = wb.cell(SC, r, 6);
    if (v === null || isErr(v) || !u) return '';
    return fmt(v, Math.abs(v) >= 100 ? '#,##0' : '0.00') + ' ' + u;
  }
  function val(n, f, unit) { var v = nm(n); return isErr(v) ? v.code : fmt(v, f) + (unit ? ' ' + unit : ''); }

  // ------------------------------------------------------------------ inputs
  var inputRows = [];
  function buildInputs() {
    var h = [];
    MODEL.inputs.forEach(function (sec) {
      h.push('<div class="bar">' + esc(sec.title) + '</div>');
      sec.rows.forEach(function (row) {
        inputRows.push(row);
        var id = 'in_' + row.name, ctl;
        if (row.pick) {
          ctl = '<select id="' + id + '"><option value="">(default)</option>' + row.pick.map(function (p) {
            return '<option>' + esc(p) + '</option>'; }).join('') + '</select>';
        } else {
          ctl = '<input id="' + id + '" ' + (row.numeric ? 'inputmode="decimal"' : 'type="text"') + ' autocomplete="off">';
        }
        h.push('<div class="row"><label for="' + id + '">' + esc(row.label) + '<span id="bd_' + row.name + '"></span></label>' +
          ctl + '<span class="u">' + esc(row.unit || '') + '</span>' +
          (row.src ? '<span class="src">' + esc(row.src) + (row.numeric && row.lo !== null && row.hi !== null ?
            ' &middot; normal ' + row.lo + ' to ' + row.hi : '') + '</span>' : '') + '</div>');
      });
    });
    $('inputs').innerHTML = h.join('');
    inputRows.forEach(function (row) {
      var el = $('in_' + row.name);
      el.addEventListener(row.pick ? 'change' : 'input', function () { setEntry(row, el.value); schedule(); save(); });
    });
  }
  function setEntry(row, raw) {
    var v = String(raw).trim();
    if (v === '') { wb.clearInput(SI, row.row, 4); return; }
    if (row.numeric) {
      var n = Number(v.replace(/,/g, ''));
      wb.setInput(SI, row.row, 4, isNaN(n) ? v : n);
    } else wb.setInput(SI, row.row, 4, v);
  }
  function entries() {
    var out = {};
    inputRows.forEach(function (row) {
      var k = wb.key(SI, row.row, 4);
      if (k in wb.inputs) out[row.name] = wb.inputs[k];
    });
    return out;
  }
  function save() { try { localStorage.setItem(STORE, JSON.stringify(entries())); } catch (e) { /* private mode */ } }
  function load() {
    var e = {};
    try { e = JSON.parse(localStorage.getItem(STORE) || '{}') || {}; } catch (x) { e = {}; }
    inputRows.forEach(function (row) {
      if (row.name in e) { setEntry(row, e[row.name]); $('in_' + row.name).value = e[row.name]; }
    });
  }
  function renderInputs() {
    inputRows.forEach(function (row) {
      var el = $('in_' + row.name), d = wb.cell(SI, row.row, 3), chk = wb.cell(SI, row.row, 9);
      var dshow = isErr(d) ? d.code : (typeof d === 'number' ? fmt(d, Math.abs(d) < 0.1 && d !== 0 ? '0.0000' : 'General') : (d || ''));
      if (row.pick) el.options[0].text = '(default: ' + dshow + ')';
      else el.placeholder = dshow === '' ? '' : 'default ' + dshow;
      var b = '';
      if (chk === 'OUT OF RANGE') b = '<span class="badge b-bad">OUT OF RANGE</span>';
      else if (chk === 'override') b = '<span class="badge b-ov">override</span>';
      $('bd_' + row.name).innerHTML = b;
    });
  }

  // ------------------------------------------------------------------ results
  function card(k, v, m, orange) {
    return '<div class="card"><div class="k">' + esc(k) + '</div><div class="v' + (orange ? ' or' : '') + '">' + esc(v) +
      '</div>' + (m ? '<div class="m">' + esc(m) + '</div>' : '') + '</div>';
  }
  function renderResults() {
    var gas = nm('d_IsGas') === 1;
    var h = ['<div class="cards">',
      card('Burner operating (LHV)', val('d_BurnerOp', '0.00', 'MMBtu/hr'), si('d_BurnerOp') + ' | HHV ' + val('d_BurnerHHV', '0.00', 'MMBtu/hr')),
      card('Burner design rating', val('d_BurnerDesign', '0.00', 'MMBtu/hr'), 'x ' + val('r_BurnerMargin', '0.00') + ' of operating'),
      card('Specific heat use', val('d_BtuLb', '#,##0', 'BTU/lb water'), si('d_BtuLb') + ' (LHV)', true),
      card('Fuel', gas ? val('d_FuelSCFH', '#,##0', 'SCFH') : val('d_mf', '#,##0', 'lb/hr'),
        (gas ? val('d_mf', '#,##0.0', 'lb/hr') + ' | ' : '') + nm('f_Fuel')),
      card('Evaporation', val('d_Evap', '#,##0', 'lb/hr'), si('d_Evap')),
      card('Product', val('d_Product', '#,##0', 'lb/hr'), val('p_MCout', '0.0') + '% MC wb'),
      card('Drum', String(nm('d_DrumSize')), 'Next up: ' + nm('d_DrumNext') + (nm('d_DrumAlt') !== '-' ? ' | smaller alternate ' + nm('d_DrumAlt') : '')),
      card('Drum checks', val('d_DrumVel', '#,##0', 'FPM'), 'VER ' + val('d_DrumVER', '0.00') + ' | fill ' + val('d_DrumFill', '0.0') +
        '% | ' + val('d_DrumRes', '0.0') + ' min | ' + val('d_DrumRPM', '0.0') + ' rpm'),
      card('Dryer exhaust', val('x_sEX_acfm', '#,##0', 'ACFM'), val('r_Texh', '0') + ' F | dew point ' + val('d_Tdew', '0') + ' F'),
      card('Inlet gas', val('x_sIN_acfm', '#,##0', 'ACFM'), val('r_Tin', '#,##0') + ' F | flame ' + val('d_Tflame', '#,##0') + ' F'),
      card('Fan', val('d_Motor', '0', 'HP motor'), val('d_BHPop', '0.0') + ' BHP hot | ' + val('d_BHPcold', '0.0') + ' BHP cold'),
      card('Annual fuel', val('d_AnnFuel', '#,##0', 'tons/yr'), val('d_AnnMMBtu', '#,##0', 'MMBtu/yr')),
      '</div>'];
    var warn = wb.values(wb.nameRange('ck_All')).filter(function (x) { return x && !isErr(x); });
    h.push('<div class="bar">Warnings (' + warn.length + ')</div>');
    if (!warn.length) h.push('<div class="ok">No warnings.</div>');
    warn.forEach(function (w) { h.push('<div class="warn">' + esc(w) + '</div>'); });
    h.push('<div class="bar">Heat balance (LHV)</div><table><tr><th>Heat use</th><th>BTU/hr</th><th>%</th><th>BTU/lb water</th></tr>');
    [['Evaporation', 'd_Qevap'], ['Solids heating', 'd_Qsolids'], ['Residual water heating', 'd_Qresid'], ['Stack', 'd_Qstack'],
      ['Shell', 'd_Qshell'], ['Furnace', 'd_Qfurnace'], ['Recycle duct', 'd_Qrecduct'], ['Burner input', 'd_Qfuel']].forEach(function (p) {
      var q = nm(p[1]), t = nm('d_Qfuel'), e = nm('d_Evap');
      h.push('<tr><td>' + p[0] + '</td><td class="n">' + fmt(q, '#,##0') + '</td><td class="n">' + fmt(q / t, '0.0%') +
        '</td><td class="n">' + fmt(q / e, '#,##0') + '</td></tr>');
    });
    h.push('</table><p class="note">Mass closure ' + val('d_CloseM', '0.0E+00') + '%, energy closure ' + val('d_CloseE', '0.0E+00') +
      '%. LHV as fired; SCFM at 70 F, 29.92 in. Hg; ACFM at site pressure.</p>');
    $('results').innerHTML = h.join('');
  }

  // ------------------------------------------------------------------ customer sheet (drawn from the workbook layout)
  var D = MODEL.diagram, colx = [0], rowy = [0], textEls = [];
  D.colpx.forEach(function (w, i) { colx[i + 1] = colx[i] + w; });
  D.rowpx.forEach(function (h, i) { rowy[i + 1] = rowy[i] + h; });
  var BW = { thin: 1, medium: 2, thick: 3, hair: 1 };
  function buildSheet() {
    var el = $('sheet'), h = [];
    var W = colx[D.cols], H = rowy[D.rows];
    el.style.width = W + 'px'; el.style.height = H + 'px';
    D.boxes.forEach(function (b) {
      var r = b[0], c = b[1], r2 = Math.min(b[4] || r, D.rows), c2 = Math.min(b[5] || c, D.cols);
      if (r > D.rows || c > D.cols) return;
      var st = 'left:' + colx[c - 1] + 'px;top:' + rowy[r - 1] + 'px;width:' + (colx[c2] - colx[c - 1]) + 'px;height:' + (rowy[r2] - rowy[r - 1]) + 'px;';
      if (b[2]) st += 'background:' + b[2] + ';';
      var bd = b[3];
      ['l', 't', 'r', 'b'].forEach(function (s) {
        if (!bd[s]) return;
        var w = BW[bd[s][0]] || 1, side = { l: 'left', t: 'top', r: 'right', b: 'bottom' }[s];
        st += 'border-' + side + ':' + w + 'px solid ' + bd[s][1] + ';';
        if (s === 'b') st += 'margin-top:' + (w > 1 ? Math.floor(w / 2) : 0) + 'px;';
      });
      h.push('<div class="bx" style="' + st + 'box-sizing:border-box"></div>');
    });
    D.imgs.forEach(function (im) {
      if (im.r > D.rows) return;
      h.push('<img alt="" src="' + MODEL.images[im.id] + '" style="left:' + (colx[im.c - 1] + im.dx) + 'px;top:' +
        (rowy[im.r - 1] + im.dy) + 'px;width:' + im.w + 'px;height:' + im.h + 'px">');
    });
    D.texts.forEach(function (t, i) {
      if (t.r > D.rows) return;
      var x = colx[t.c - 1], y = rowy[t.r - 1], w = colx[t.c2] - x, hh = rowy[t.r2] - y;
      var jc = t.h === 'center' ? 'center' : t.h === 'right' ? 'flex-end' : 'flex-start';
      var ai = t.v === 'top' ? 'flex-start' : t.v === 'center' ? 'center' : 'flex-end';
      var st = 'left:' + x + 'px;top:' + y + 'px;width:' + w + 'px;height:' + hh + 'px;justify-content:' + jc + ';align-items:' + ai +
        ';font-family:' + (t.head ? 'var(--head)' : 'var(--body)') + ';font-size:' + (t.sz * 96 / 72) + 'px;color:' + t.color +
        ';font-weight:' + (t.b ? 700 : 400) + ';' + (t.i ? 'font-style:italic;' : '') + (t.indent ? 'padding-left:' + (t.indent * 9) + 'px;' : '') +
        (t.wrap ? '' : (t.h === 'center' ? '' : t.h === 'right' ? 'direction:rtl;' : ''));
      h.push('<div class="tx' + (t.wrap ? ' wrap' : '') + '" id="tx' + i + '" style="' + st + '"></div>');
    });
    el.innerHTML = h.join('');
    textEls = D.texts.map(function (t, i) { return $('tx' + i); });
    fitSheet();
  }
  function renderSheet() {
    D.texts.forEach(function (t, i) {
      var el = textEls[i]; if (!el) return;
      var v = wb.cell(D.sheet, t.r, t.c);
      var s = (typeof v === 'number') ? fmt(v, t.fmt) : isErr(v) ? v.code : (v === null ? '' : String(v));
      el.textContent = s;
      if (el.style.direction === 'rtl') { el.style.direction = 'ltr'; el.style.justifyContent = 'flex-end'; }
    });
  }
  function fitSheet() {
    var wrap = $('sheetWrap'), el = $('sheet');
    var W = colx[D.cols], H = rowy[D.rows];
    var avail = wrap.clientWidth || W, k = Math.min(1, avail / W);
    el.style.transform = 'scale(' + k + ')';
    wrap.style.height = (H * k) + 'px';
  }

  // ------------------------------------------------------------------ calculation table
  function renderCalc() {
    var h = ['<table class="calc"><tr><th>Item</th><th>Value</th><th>Unit</th><th>Metric</th><th></th><th>Method / note</th></tr>'];
    MODEL.calc.forEach(function (c) {
      if (c.section) { h.push('<tr><td colspan="6"><div class="bar" style="margin:8px 0 2px">' + esc(c.section) + '</div></td></tr>'); return; }
      var v = wb.cell(SC, c.row, 3), s = '';
      if (c.si) { var sv = wb.cell(SC, c.row, 5); s = isErr(sv) ? sv.code : fmt(sv, '#,##0.00'); }
      var shown = typeof v === 'number' ? fmt(v, c.fmt) : isErr(v) ? v.code : (v === null ? '' : String(v));
      h.push('<tr><td>' + esc(c.label) + (c.name ? ' <span class="note">' + esc(c.name) + '</span>' : '') + '</td><td>' + esc(shown) +
        '</td><td>' + esc(c.unit) + '</td><td>' + esc(s) + '</td><td>' + esc(c.si_unit) + '</td><td class="note">' + esc(c.note) + '</td></tr>');
    });
    h.push('</table>');
    $('calc').innerHTML = h.join('');
  }

  // ------------------------------------------------------------------ render loop
  var pending = false, active = 't-inputs';
  function render() {
    pending = false;
    wb.reset();
    renderInputs();
    if (active === 't-results') renderResults();
    if (active === 't-sheet') { renderSheet(); fitSheet(); }
    if (active === 't-calc') renderCalc();
  }
  function schedule() { if (!pending) { pending = true; (window.requestAnimationFrame || setTimeout)(render); } }

  // ------------------------------------------------------------------ record
  var KEY = ['d_Evap', 'd_Product', 'd_mf', 'd_BurnerOp', 'd_BurnerHHV', 'd_BurnerDesign', 'd_BtuLb', 'd_DrumSize', 'd_DrumNext',
    'd_DrumAlt', 'x_sEX_acfm', 'x_sIN_scfm', 'd_Tdew', 'd_BHPop', 'd_Motor', 'd_Tflame', 'd_CloseE', 'd_CloseM'];
  function record() {
    var res = {};
    KEY.forEach(function (k) { var v = nm(k); res[k] = isErr(v) ? v.code : v; });
    return { contract: 'mce.dryer.workbook.v1', calculator: MODEL.version, timestamp: new Date().toISOString(),
      entries: entries(), results: res,
      warnings: wb.values(wb.nameRange('ck_All')).filter(function (x) { return x && !isErr(x); }) };
  }
  $('download').addEventListener('click', function () {
    var rec = record(), a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(rec, null, 2)], { type: 'application/json' }));
    a.download = 'rotary_dryer_' + (rec.entries.j_Job || 'case') + '_' + rec.timestamp.slice(0, 10) + '.json';
    document.body.appendChild(a); a.click(); a.remove();
  });
  $('save').addEventListener('click', function () {
    var msg = $('saveMsg');
    if (location.protocol === 'file:') { msg.textContent = 'Saving a sizing record needs the MCE server or quote app. Use Download record instead.'; return; }
    msg.textContent = 'Saving...';
    fetch('api/dryer/workbook', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(record()) })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        if (r.status !== 'ok') { msg.textContent = 'Not saved: ' + (r.error || r.message || 'error'); return; }
        var row = inputRows.filter(function (x) { return x.name === 'j_Record'; })[0];
        if (row) { wb.setInput(SI, row.row, 4, r.record.index); $('in_j_Record').value = r.record.index; save(); }
        msg.textContent = 'Saved as sizing record ' + r.record.index + '. Engine cross-check: ' + r.crosscheck.summary;
        schedule();
      })
      .catch(function () { msg.textContent = 'Server not reachable. Use Download record instead.'; });
  });
  $('xlsx').addEventListener('click', function () {
    var msg = $('saveMsg');
    if (location.protocol === 'file:') { msg.textContent = 'The Excel download needs the MCE server or quote app.'; return; }
    msg.textContent = 'Building the workbook...';
    fetch('api/dryer/workbook/xlsx', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(record()) })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        var cd = r.headers.get('Content-Disposition') || '', m = /filename="([^"]+)"/.exec(cd);
        return r.blob().then(function (b) { return [b, m ? m[1] : 'MCE_rotary_dryer.xlsx']; });
      })
      .then(function (x) {
        var a = document.createElement('a'); a.href = URL.createObjectURL(x[0]); a.download = x[1];
        document.body.appendChild(a); a.click(); a.remove(); msg.textContent = 'Excel workbook downloaded: ' + x[1];
      })
      .catch(function (e) { msg.textContent = 'Excel download failed: ' + e.message; });
  });
  $('print').addEventListener('click', function () { window.print(); });
  window.addEventListener('beforeprint', function () {  // letter landscape, 0.3 in margins: 10.4 x 7.9 in
    var el = $('sheet'), W = colx[D.cols], H = rowy[D.rows];
    var k = Math.min(1, 10.3 * 96 / W, 7.8 * 96 / H);
    renderSheet(); el.style.transform = 'scale(' + k + ')';
    $('sheetWrap').style.width = (W * k) + 'px'; $('sheetWrap').style.height = (H * k) + 'px';
  });
  window.addEventListener('afterprint', function () { $('sheetWrap').style.width = ''; fitSheet(); });
  $('reset').addEventListener('click', function () {
    inputRows.forEach(function (row) { wb.clearInput(SI, row.row, 4); $('in_' + row.name).value = ''; });
    save(); schedule();
  });
  document.querySelectorAll('nav button').forEach(function (b) {
    b.addEventListener('click', function () {
      document.querySelectorAll('nav button').forEach(function (x) { x.classList.toggle('on', x === b); });
      document.querySelectorAll('section.tab').forEach(function (s) { s.classList.toggle('on', s.id === b.dataset.t); });
      active = b.dataset.t; schedule();
    });
  });
  window.addEventListener('resize', fitSheet);
  $('ver').textContent = MODEL.version;

  buildInputs();
  load();
  buildSheet();
  render();
  window.mceDryer = { wb: wb, entries: entries, record: record, render: render };
})();
