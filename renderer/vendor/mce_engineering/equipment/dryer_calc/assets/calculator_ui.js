/* MCE rotary dryer calculator UI. All numbers come from the workbook's formulas via xlcalc (MODEL).
   Simple screen: product, throughput, moisture in and out, fuel, elevation. Everything else stays at the workbook
   default and can be changed under "All inputs" or in the Excel download. */
(function () {
  'use strict';
  var wb = new xlcalc.Workbook(MODEL);
  var S = {};
  MODEL.sheets.forEach(function (n, i) { S[n] = i; });
  var SI = S['Inputs'], SC = S['Calc'];
  var fmt = xlcalc.format, isErr = xlcalc.isErr;
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var STORE = 'mce-dryer-entries-v2';
  var SIMPLE = ['j_Job', 'j_Customer', 'p_Material', 'p_Throughput', 'p_TUnit', 'p_TBasis', 'p_MCin', 'p_MCout', 'f_Fuel', 's_Elev'];
  var LABELS = { p_TBasis: { wet_feed: 'Wet infeed', product: 'Dried product' } };

  function nm(n) { return wb.name(n); }
  function num(n) { var v = nm(n); return typeof v === 'number' ? v : NaN; }
  function val(n, f, unit) { var v = nm(n); return isErr(v) ? v.code : fmt(v, f) + (unit ? ' ' + unit : ''); }

  // ------------------------------------------------------------------ inputs
  var rows = {}, inputRows = [];
  MODEL.inputs.forEach(function (sec) { sec.rows.forEach(function (r) { rows[r.name] = r; inputRows.push(r); }); });

  function control(row, id) {
    if (row.pick) {
      var opts = row.pick;
      if (LABELS[row.name]) opts = Object.keys(LABELS[row.name]);
      return '<select id="' + id + '">' + opts.map(function (p) {
        return '<option value="' + esc(p) + '">' + esc(LABELS[row.name] ? LABELS[row.name][p] : p) + '</option>'; }).join('') + '</select>';
    }
    return '<input id="' + id + '" ' + (row.numeric ? 'inputmode="decimal"' : 'type="text"') + ' autocomplete="off">';
  }
  function buildSimple() {
    var f = function (name, label, unit, wide) {
      var row = rows[name];
      return '<div class="f' + (wide ? ' wide' : '') + '"><label for="in_' + name + '">' + esc(label) +
        '<span id="bd_' + name + '"></span></label><div class="ctl">' + control(row, 'in_' + name) +
        (unit ? '<span class="u">' + esc(unit) + '</span>' : '') + '</div></div>';
    };
    $('simple').innerHTML = [
      f('p_Material', 'Product', '', true),
      '<div class="f"><label for="in_p_Throughput">Throughput<span id="bd_p_Throughput"></span></label><div class="ctl">' +
        control(rows.p_Throughput, 'in_p_Throughput') + control(rows.p_TUnit, 'in_p_TUnit') + '</div></div>',
      f('p_TBasis', 'Rate is of the', ''),
      f('p_MCin', 'Moisture in', '% wb'),
      f('p_MCout', 'Moisture out', '% wb'),
      f('f_Fuel', 'Fuel', '', true),
      f('s_Elev', 'Site elevation', 'ft'),
      f('j_Job', 'Job number (optional)', ''),
      f('j_Customer', 'Customer (optional)', '')
    ].join('');
  }
  function buildAdvanced() {
    var h = [];
    MODEL.inputs.forEach(function (sec) {
      var rs = sec.rows.filter(function (r) { return SIMPLE.indexOf(r.name) < 0; });
      if (!rs.length) return;
      h.push('<div class="bar">' + esc(sec.title) + '</div>');
      rs.forEach(function (row) {
        var id = 'in_' + row.name, ctl;
        if (row.pick) {
          ctl = '<select id="' + id + '"><option value="">(default)</option>' + row.pick.map(function (p) {
            return '<option>' + esc(p) + '</option>'; }).join('') + '</select>';
        } else ctl = control(row, id);
        h.push('<div class="row"><label for="' + id + '">' + esc(row.label) + '<span id="bd_' + row.name + '"></span></label>' +
          ctl + '<span class="u">' + esc(row.unit || '') + '</span>' +
          (row.src ? '<span class="src">' + esc(row.src) + (row.numeric && row.lo !== null && row.hi !== null ?
            ' &middot; normal ' + row.lo + ' to ' + row.hi : '') + '</span>' : '') + '</div>');
      });
    });
    $('inputs').innerHTML = h.join('');
  }
  function bind() {
    inputRows.forEach(function (row) {
      var el = $('in_' + row.name);
      if (!el) return;
      el.addEventListener(el.tagName === 'SELECT' ? 'change' : 'input', function () { setEntry(row, el.value); schedule(); save(); });
    });
  }
  function dflt(row) { return wb.cell(SI, row.row, 3); }
  function setEntry(row, raw) {
    var v = String(raw).trim();
    var simpleSel = SIMPLE.indexOf(row.name) >= 0 && row.pick;
    if (v === '' || (simpleSel && v === String(dflt(row)))) { wb.clearInput(SI, row.row, 4); return; }
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
      if (row.name in e && $('in_' + row.name)) { setEntry(row, e[row.name]); $('in_' + row.name).value = e[row.name]; }
    });
  }
  function renderInputs() {
    var nOver = 0;
    inputRows.forEach(function (row) {
      var el = $('in_' + row.name);
      if (!el) return;
      var d = dflt(row), chk = wb.cell(SI, row.row, 9), set = (wb.key(SI, row.row, 4) in wb.inputs);
      var dshow = isErr(d) ? d.code : (typeof d === 'number' ? fmt(d, Math.abs(d) < 0.1 && d !== 0 ? '0.0000' : 'General') : (d || ''));
      var simple = SIMPLE.indexOf(row.name) >= 0;
      if (el.tagName === 'SELECT') {
        if (simple) { if (!set) el.value = String(d); }
        else el.options[0].text = '(default: ' + dshow + ')';
      } else el.placeholder = dshow === '' ? '' : (simple ? dshow : 'default ' + dshow);
      var b = '';
      if (chk === 'OUT OF RANGE') b = '<span class="badge b-bad">OUT OF RANGE</span>';
      else if (chk === 'override' && !simple) { b = '<span class="badge b-ov">override</span>'; nOver++; }
      var bd = $('bd_' + row.name); if (bd) bd.innerHTML = b;
    });
    $('advCount').textContent = nOver ? ' (' + nOver + ' changed)' : '';
    var mat = nm('p_Material');
    $('prodNote').textContent = 'Cp ' + val('p_Cp', '0.000') + ' BTU/lb-F dry solids, bulk density ' + val('p_RhoDry', '0.0') +
      ' lb/ft3 dry, typical ' + val('p_MCin', '0') + '% to ' + val('p_MCout', '0') + '%, discharge ' + val('p_ProdT', '0') +
      ' F. Values from the product library (' + String(mat) + '); change any of them under All inputs.';
  }

  // ------------------------------------------------------------------ results
  function card(k, v, m, orange) {
    return '<div class="card"><div class="k">' + esc(k) + '</div><div class="v' + (orange ? ' or' : '') + '">' + esc(v) +
      '</div>' + (m ? '<div class="m">' + esc(m) + '</div>' : '') + '</div>';
  }
  function fuelRate() {
    var kind = nm('d_FuelKind');
    if (kind === 'gas') return [val('d_FuelSCFH', '#,##0', 'SCFH'), val('d_mf', '#,##0', 'lb/hr')];
    if (kind === 'liquid') return [val('d_FuelGal', '#,##0.0', 'gal/hr'), val('d_mf', '#,##0', 'lb/hr')];
    return [val('d_mf', '#,##0', 'lb/hr'), val('f_MC', '0') + '% MC wood fuel'];
  }
  function renderResults() {
    var fr = fuelRate(), self = num('d_SelfFuel') === 1;
    var h = ['<div class="cards">',
      card('Burner size', val('d_BurnerDesign', '0.00', 'MMBtu/hr'), 'design rating; ' + val('d_BurnerOp', '0.00') + ' MMBtu/hr operating (LHV)', true),
      card('Fuel use', fr[0], fr[1] + ' | ' + val('d_AnnMMBtu', '#,##0') + ' MMBtu/yr'),
      card('Water evaporated', val('d_Evap', '#,##0', 'lb/hr'), val('d_Wet', '#,##0') + ' lb/hr wet in'),
      card('Dried product', val('d_Product', '#,##0', 'lb/hr'), self ? val('d_NetProduct', '#,##0') + ' lb/hr net after the burner fuel'
        : val('d_AnnProduct', '#,##0') + ' tons/yr'),
      card('Rotary drum', String(nm('d_DrumSize')), val('d_DrumRPM', '0.0') + ' rpm | ' + val('d_DrumRes', '0') + ' min residence', true),
      card('Exhaust air', val('x_sEX_acfm', '#,##0', 'ACFM'), 'at ' + val('r_Texh', '0') + ' F; inlet ' + val('r_Tin', '#,##0') + ' F'),
      card('Exhaust fan', val('d_Motor', '0', 'HP motor'), val('d_BHPop', '0.0') + ' BHP at ' + val('d_SPop', '0.0') + ' in. w.c.'),
      card('Energy per lb water', val('d_BtuLb', '#,##0', 'BTU/lb'), 'LHV; typical 1,400 to 1,900'),
      '</div>'];
    // emissions
    h.push('<div class="bar">Emissions estimate</div><table><tr><th>Pollutant</th><th class="n">lb/hr</th><th class="n">tons/yr*</th>' +
      '<th class="n">PTE tons/yr</th></tr>');
    [['NOx', 'NOx'], ['CO', 'CO'], ['SO2', 'SO2'], ['PM', 'PM (stack)'], ['VOC', 'VOC'], ['CO2', 'CO2']].forEach(function (p) {
      h.push('<tr><td>' + p[1] + '</td><td class="n">' + val('em_' + p[0] + '_lb', p[0] === 'CO2' ? '#,##0' : '0.00') + '</td><td class="n">' +
        val('em_' + p[0] + '_tpy', '#,##0.0') + '</td><td class="n">' + val('em_' + p[0] + '_pte', '#,##0.0') + '</td></tr>');
    });
    h.push('</table><p class="note">' + esc(String(nm('em_Summary'))) + ' *At ' + val('p_Hours', '#,##0') + ' hr/yr; PTE at 8,760 hr/yr. ' +
      'AP-42 screening factors; details and sources on the Emissions sheet of the Excel workbook.</p>');
    var warn = wb.values(wb.nameRange('ck_All')).filter(function (x) { return x && !isErr(x); });
    h.push('<div class="bar">Warnings (' + warn.length + ')</div>');
    if (!warn.length) h.push('<div class="ok">No warnings.</div>');
    warn.forEach(function (w) { h.push('<div class="warn">' + esc(w) + '</div>'); });
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
      el.textContent = (typeof v === 'number') ? fmt(v, t.fmt) : isErr(v) ? v.code : (v === null ? '' : String(v));
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
  var pending = false;
  function open(id) { return $(id).open; }
  function render() {
    pending = false;
    wb.reset();
    renderInputs();
    renderResults();
    if (open('d-sheet')) { renderSheet(); fitSheet(); }
    if (open('d-calc')) renderCalc();
  }
  function schedule() { if (!pending) { pending = true; (window.requestAnimationFrame || setTimeout)(render); } }

  // ------------------------------------------------------------------ record
  var KEY = ['d_Evap', 'd_Product', 'd_mf', 'd_BurnerOp', 'd_BurnerHHV', 'd_BurnerDesign', 'd_BtuLb', 'd_DrumSize', 'd_DrumNext',
    'd_DrumAlt', 'x_sEX_acfm', 'x_sIN_scfm', 'd_Tdew', 'd_BHPop', 'd_Motor', 'd_Tflame', 'd_CloseE', 'd_CloseM',
    'em_NOx_pte', 'em_CO_pte', 'em_PM_pte', 'em_VOC_pte', 'em_CO2_pte'];
  function record() {
    var res = {};
    KEY.forEach(function (k) { var v = nm(k); res[k] = isErr(v) ? v.code : v; });
    return { contract: 'mce.dryer.workbook.v1', calculator: MODEL.version, timestamp: new Date().toISOString(),
      entries: entries(), results: res,
      warnings: wb.values(wb.nameRange('ck_All')).filter(function (x) { return x && !isErr(x); }) };
  }
  function msg(t) { $('saveMsg').textContent = t; }
  $('save').addEventListener('click', function () {
    if (location.protocol === 'file:') { msg('Saving a sizing record needs the MCE server or quote app.'); return; }
    msg('Saving...');
    fetch('api/dryer/workbook', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(record()) })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        if (r.status !== 'ok') { msg('Not saved: ' + (r.error || r.message || 'error')); return; }
        var row = rows.j_Record;
        if (row) { wb.setInput(SI, row.row, 4, r.record.index); if ($('in_j_Record')) $('in_j_Record').value = r.record.index; save(); }
        msg('Saved as sizing record ' + r.record.index + '. Engine cross-check: ' + r.crosscheck.summary);
        schedule();
      })
      .catch(function () { msg('Server not reachable. Use Download Excel later or the record JSON.'); });
  });
  $('xlsx').addEventListener('click', function () {
    if (location.protocol === 'file:') { msg('The Excel download needs the MCE server or quote app.'); return; }
    msg('Building the workbook...');
    fetch('api/dryer/workbook/xlsx', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(record()) })
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        var cd = r.headers.get('Content-Disposition') || '', m = /filename="([^"]+)"/.exec(cd);
        return r.blob().then(function (b) { return [b, m ? m[1] : 'MCE_rotary_dryer.xlsx']; });
      })
      .then(function (x) {
        var a = document.createElement('a'); a.href = URL.createObjectURL(x[0]); a.download = x[1];
        document.body.appendChild(a); a.click(); a.remove(); msg('Excel workbook downloaded: ' + x[1]);
      })
      .catch(function (e) { msg('Excel download failed: ' + e.message); });
  });
  $('download').addEventListener('click', function () {
    var rec = record(), a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify(rec, null, 2)], { type: 'application/json' }));
    a.download = 'rotary_dryer_' + (rec.entries.j_Job || 'case') + '_' + rec.timestamp.slice(0, 10) + '.json';
    document.body.appendChild(a); a.click(); a.remove();
  });
  $('print').addEventListener('click', function () { $('d-sheet').open = true; render(); window.print(); });
  window.addEventListener('beforeprint', function () {  // letter landscape, 0.3 in margins: 10.4 x 7.9 in
    var el = $('sheet'), W = colx[D.cols], H = rowy[D.rows];
    var k = Math.min(1, 10.3 * 96 / W, 7.8 * 96 / H);
    renderSheet(); el.style.transform = 'scale(' + k + ')';
    $('sheetWrap').style.width = (W * k) + 'px'; $('sheetWrap').style.height = (H * k) + 'px';
  });
  window.addEventListener('afterprint', function () { $('sheetWrap').style.width = ''; fitSheet(); });
  $('reset').addEventListener('click', function () {
    inputRows.forEach(function (row) { wb.clearInput(SI, row.row, 4); var el = $('in_' + row.name); if (el) el.value = ''; });
    save(); schedule();
  });
  ['d-sheet', 'd-calc'].forEach(function (id) { $(id).addEventListener('toggle', schedule); });
  window.addEventListener('resize', fitSheet);
  $('ver').textContent = MODEL.version;

  buildSimple();
  buildAdvanced();
  bind();
  load();
  buildSheet();
  render();
  window.mceDryer = { wb: wb, entries: entries, record: record, render: render };
})();
