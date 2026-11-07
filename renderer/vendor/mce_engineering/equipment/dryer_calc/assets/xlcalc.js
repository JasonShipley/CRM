/* xlcalc: evaluates the MCE rotary dryer workbook's own formulas in the browser (and in Node for tests).
 *
 * The model is exported from the .xlsx by html_calc.py: every formula cell keeps its Excel formula, with
 * cell references rewritten to R1C1 so rows that share a formula share one parsed template. Supported: the
 * operators + - * / ^ & = <> < > <= >= and unary minus, ranges, defined names, and the functions the workbook
 * uses (IF AND OR PI MAX MIN SQRT EXP ABS ROUND FLOOR SUM SUMPRODUCT INDEX MATCH MINIFS COUNTIF TEXT
 * TEXTJOIN TODAY LOWER). Nothing here knows any dryer math: it is a small spreadsheet engine.
 */
(function (root) {
  'use strict';

  function XLError(code) { this.code = code; }
  XLError.prototype.toString = function () { return this.code; };
  var ERR = {
    VALUE: new XLError('#VALUE!'), NAME: new XLError('#NAME?'), REF: new XLError('#REF!'),
    DIV0: new XLError('#DIV/0!'), NA: new XLError('#N/A'), NUM: new XLError('#NUM!')
  };
  function isErr(v) { return v instanceof XLError; }

  // ------------------------------------------------------------------ tokenizer
  var RE = {
    ws: /^\s+/,
    num: /^(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)/,
    str: /^"((?:[^"]|"")*)"/,
    ref: /^(?:('(?:[^']|'')+'|[A-Za-z][A-Za-z0-9_\-]*)!)?R(\[-?\d+\]|\d+)C(\[-?\d+\]|\d+)/,
    ident: /^[A-Za-z_][A-Za-z0-9_.]*/,
    op: /^(<>|<=|>=|[-+*\/^&=<>:,()])/
  };

  function tokenize(src) {
    var out = [], s = src, m;
    while (s.length) {
      if ((m = RE.ws.exec(s))) { s = s.slice(m[0].length); continue; }
      if ((m = RE.str.exec(s))) { out.push({ t: 'str', v: m[1].replace(/""/g, '"') }); s = s.slice(m[0].length); continue; }
      if ((m = RE.ref.exec(s))) {
        var sheet = m[1] ? m[1].replace(/^'|'$/g, '').replace(/''/g, "'") : null;
        out.push({ t: 'ref', sheet: sheet, r: part(m[2]), c: part(m[3]) });
        s = s.slice(m[0].length); continue;
      }
      if ((m = RE.num.exec(s))) { out.push({ t: 'num', v: parseFloat(m[1]) }); s = s.slice(m[0].length); continue; }
      if ((m = RE.ident.exec(s))) {
        var id = m[0]; s = s.slice(id.length);
        if (/^\s*\(/.test(s)) out.push({ t: 'fn', v: id.replace(/^_xlfn\./i, '').toUpperCase() });
        else if (/^(TRUE|FALSE)$/i.test(id)) out.push({ t: 'bool', v: id.toUpperCase() === 'TRUE' });
        else out.push({ t: 'name', v: id });
        continue;
      }
      if ((m = RE.op.exec(s))) { out.push({ t: 'op', v: m[1] }); s = s.slice(m[0].length); continue; }
      throw new Error('cannot tokenize: ' + s.slice(0, 30));
    }
    return out;
  }
  function part(p) {  // "[−3]" relative or "5" absolute
    return p.charAt(0) === '[' ? { rel: true, n: parseInt(p.slice(1, -1), 10) } : { rel: false, n: parseInt(p, 10) };
  }

  // ------------------------------------------------------------------ parser (Excel precedence)
  function parse(src) {
    var toks = tokenize(src), i = 0;
    function peek() { return toks[i]; }
    function isOp(v) { var t = toks[i]; return t && t.t === 'op' && t.v === v; }
    function take(v) { if (!isOp(v)) throw new Error('expected ' + v + ' in ' + src); i++; }
    function cmp() {
      var a = cat();
      while (peek() && peek().t === 'op' && /^(=|<>|<|>|<=|>=)$/.test(peek().v)) { var op = toks[i++].v; a = { k: 'bin', op: op, a: a, b: cat() }; }
      return a;
    }
    function cat() { var a = add(); while (isOp('&')) { i++; a = { k: 'bin', op: '&', a: a, b: add() }; } return a; }
    function add() {
      var a = mul();
      while (isOp('+') || isOp('-')) { var op = toks[i++].v; a = { k: 'bin', op: op, a: a, b: mul() }; }
      return a;
    }
    function mul() {
      var a = pow();
      while (isOp('*') || isOp('/')) { var op = toks[i++].v; a = { k: 'bin', op: op, a: a, b: pow() }; }
      return a;
    }
    function pow() { var a = unary(); while (isOp('^')) { i++; a = { k: 'bin', op: '^', a: a, b: unary() }; } return a; }
    function unary() {
      if (isOp('-')) { i++; return { k: 'neg', a: unary() }; }
      if (isOp('+')) { i++; return unary(); }
      return primary();
    }
    function primary() {
      var t = toks[i++];
      if (!t) throw new Error('unexpected end in ' + src);
      if (t.t === 'num') return { k: 'num', v: t.v };
      if (t.t === 'str') return { k: 'str', v: t.v };
      if (t.t === 'bool') return { k: 'bool', v: t.v };
      if (t.t === 'name') return { k: 'name', n: t.v };
      if (t.t === 'ref') {
        var node = { k: 'ref', sheet: t.sheet, r: t.r, c: t.c };
        if (isOp(':')) {
          i++; var u = toks[i++];
          if (!u || u.t !== 'ref') throw new Error('bad range in ' + src);
          return { k: 'range', a: node, b: { k: 'ref', sheet: t.sheet, r: u.r, c: u.c } };
        }
        return node;
      }
      if (t.t === 'fn') {
        take('('); var args = [];
        if (!isOp(')')) { args.push(cmp()); while (isOp(',')) { i++; args.push(cmp()); } }
        take(')');
        return { k: 'fn', n: t.v, args: args };
      }
      if (t.t === 'op' && t.v === '(') { var e = cmp(); take(')'); return e; }
      throw new Error('unexpected ' + JSON.stringify(t) + ' in ' + src);
    }
    var ast = cmp();
    if (i !== toks.length) throw new Error('trailing tokens in ' + src);
    return ast;
  }

  // ------------------------------------------------------------------ value helpers
  function Range(s, r1, c1, r2, c2) { this.s = s; this.r1 = r1; this.c1 = c1; this.r2 = r2; this.c2 = c2; }
  function toNum(v) {
    if (v === null || v === undefined || v === '') return 0;
    if (typeof v === 'number') return v;
    if (typeof v === 'boolean') return v ? 1 : 0;
    if (isErr(v)) return v;
    var n = Number(v);
    return isNaN(n) ? ERR.VALUE : n;
  }
  function toBool(v) {
    if (isErr(v)) return v;
    if (typeof v === 'boolean') return v;
    if (v === null || v === undefined || v === '') return false;
    if (typeof v === 'number') return v !== 0;
    if (/^true$/i.test(v)) return true;
    if (/^false$/i.test(v)) return false;
    return ERR.VALUE;
  }
  function general(n) {
    if (Number.isInteger(n)) return String(n);
    var s = String(parseFloat(n.toPrecision(10)));
    return s;
  }
  function toStr(v) {
    if (v === null || v === undefined) return '';
    if (typeof v === 'number') return general(v);
    if (typeof v === 'boolean') return v ? 'TRUE' : 'FALSE';
    return String(v);
  }
  function compare(a, b) {  // Excel ordering: numbers < text < logical; text case-insensitive
    if (a === null || a === undefined) a = typeof b === 'string' ? '' : typeof b === 'boolean' ? false : 0;
    if (b === null || b === undefined) b = typeof a === 'string' ? '' : typeof a === 'boolean' ? false : 0;
    var rank = function (x) { return typeof x === 'number' ? 0 : typeof x === 'string' ? 1 : 2; };
    var ra = rank(a), rb = rank(b);
    if (ra !== rb) return ra < rb ? -1 : 1;
    if (ra === 1) { a = a.toLowerCase(); b = b.toLowerCase(); }
    return a < b ? -1 : a > b ? 1 : 0;
  }

  // ------------------------------------------------------------------ number formats (TEXT and display)
  function excelDate(serial) { return new Date(Date.UTC(1899, 11, 30) + Math.round(serial) * 86400000); }
  function addCommas(s) {
    var p = s.split('.'), neg = p[0].charAt(0) === '-';
    var d = neg ? p[0].slice(1) : p[0];
    d = d.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    return (neg ? '-' : '') + d + (p.length > 1 ? '.' + p[1] : '');
  }
  function format(v, fmt) {
    if (isErr(v)) return v.code;
    if (v === null || v === undefined) return '';
    if (typeof v !== 'number') return toStr(v);
    if (!fmt || fmt === 'General' || fmt === '@') return general(v);
    if (fmt === 'm/d/yyyy') { var d = excelDate(v); return (d.getUTCMonth() + 1) + '/' + d.getUTCDate() + '/' + d.getUTCFullYear(); }
    var pct = /%$/.test(fmt), x = pct ? v * 100 : v;
    var dec = (fmt.split('.')[1] || '').replace(/[^0]/g, '').length;
    if (/E\+/i.test(fmt)) {
      var m = (fmt.split('.')[1] || '').split(/E/i)[0].length;
      var s = x.toExponential(m).replace('e', 'E');
      s = s.replace(/E([+-])(\d)$/, 'E$10$2');
      return s;
    }
    var out = (Math.round(x * Math.pow(10, dec)) / Math.pow(10, dec)).toFixed(dec);
    if (out === '-0' || /^-0\.0*$/.test(out)) out = out.slice(1);
    if (fmt.indexOf(',') >= 0) out = addCommas(out);
    return out + (pct ? '%' : '');
  }

  // ------------------------------------------------------------------ criteria (MINIFS, COUNTIF)
  function criterion(c) {
    if (typeof c === 'number') return function (v) { return typeof v === 'number' && v === c; };
    var s = toStr(c), m = /^(<=|>=|<>|<|>|=)(.*)$/.exec(s);
    var op = m ? m[1] : '=', rhs = m ? m[2] : s, n = Number(rhs), numeric = rhs !== '' && !isNaN(n);
    return function (v) {
      if (numeric) {
        if (typeof v !== 'number') return op === '<>';
        return op === '=' ? v === n : op === '<>' ? v !== n : op === '<' ? v < n : op === '>' ? v > n :
          op === '<=' ? v <= n : v >= n;
      }
      var eq = toStr(v).toLowerCase() === rhs.toLowerCase();
      return op === '<>' ? !eq : eq;
    };
  }

  // ------------------------------------------------------------------ workbook
  function Workbook(model) {
    this.model = model;
    this.sheetIndex = {};
    for (var k = 0; k < model.sheets.length; k++) this.sheetIndex[model.sheets[k]] = k;
    this.asts = new Array(model.templates.length);
    this.inputs = {};  // "s,r,c" -> value typed by the user
    this.memo = {};
    this.today = Math.floor((Date.now() - Date.UTC(1899, 11, 30)) / 86400000);
  }
  var W = Workbook.prototype;
  W.key = function (s, r, c) { return s + ',' + r + ',' + c; };
  W.reset = function () { this.memo = {}; };
  W.setInput = function (s, r, c, v) { this.inputs[this.key(s, r, c)] = v; this.memo = {}; };
  W.clearInput = function (s, r, c) { delete this.inputs[this.key(s, r, c)]; this.memo = {}; };
  W.raw = function (s, r, c) { var row = this.model.cells[s][r]; return row ? row[c] : undefined; };
  W.cell = function (s, r, c) {
    var k = this.key(s, r, c);
    if (k in this.inputs) return this.inputs[k];
    if (k in this.memo) return this.memo[k];
    var raw = this.raw(s, r, c), v;
    if (raw === undefined || raw === null) v = null;
    else if (typeof raw === 'object' && 'f' in raw) {
      this.memo[k] = ERR.REF;  // cycle guard
      var ast = this.asts[raw.f] || (this.asts[raw.f] = parse(this.model.templates[raw.f]));
      v = this.deref(this.ev(ast, s, r, c));
      if (v instanceof Range) v = ERR.VALUE;
    } else v = raw;
    this.memo[k] = v;
    return v;
  };
  W.resolve = function (node, s, r, c) {
    var sh = node.sheet ? this.sheetIndex[node.sheet] : s;
    return [sh, node.r.rel ? r + node.r.n : node.r.n, node.c.rel ? c + node.c.n : node.c.n];
  };
  W.nameRange = function (n) {
    var d = this.model.names[n];
    if (!d) return ERR.NAME;
    return new Range(d[0], d[1], d[2], d[3], d[4]);
  };
  W.values = function (rg) {  // flattened values of a range, row-major
    var out = [];
    for (var r = rg.r1; r <= rg.r2; r++) for (var c = rg.c1; c <= rg.c2; c++) out.push(this.cell(rg.s, r, c));
    return out;
  };
  W.deref = function (v) {
    if (v instanceof Range) {
      if (v.r1 === v.r2 && v.c1 === v.c2) return this.cell(v.s, v.r1, v.c1);
      return v;
    }
    return v;
  };
  W.arr = function (v) {  // value -> array for elementwise use
    if (v instanceof Range) return this.values(v);
    return v;
  };
  W.ev = function (n, s, r, c) {
    switch (n.k) {
      case 'num': case 'str': case 'bool': return n.v;
      case 'name': {
        var d = this.model.names[n.n];
        if (!d) { if (/^(TRUE|FALSE)$/i.test(n.n)) return /^TRUE$/i.test(n.n); return ERR.NAME; }
        var rg = this.nameRange(n.n);
        return (rg.r1 === rg.r2 && rg.c1 === rg.c2) ? this.cell(rg.s, rg.r1, rg.c1) : rg;
      }
      case 'ref': { var p = this.resolve(n, s, r, c); return this.cell(p[0], p[1], p[2]); }
      case 'range': {
        var a = this.resolve(n.a, s, r, c), b = this.resolve(n.b, s, r, c);
        return new Range(a[0], Math.min(a[1], b[1]), Math.min(a[2], b[2]), Math.max(a[1], b[1]), Math.max(a[2], b[2]));
      }
      case 'neg': return this.map1(this.arr(this.ev(n.a, s, r, c)), function (x) { x = toNum(x); return isErr(x) ? x : -x; });
      case 'bin': return this.binop(n.op, this.arr(this.ev(n.a, s, r, c)), this.arr(this.ev(n.b, s, r, c)));
      case 'fn': return this.call(n.n, n.args, s, r, c);
    }
    throw new Error('bad node ' + n.k);
  };
  W.map1 = function (a, f) { return Array.isArray(a) ? a.map(f) : f(a); };
  W.binop = function (op, a, b) {
    if (Array.isArray(a) || Array.isArray(b)) {
      var n = Array.isArray(a) ? a.length : b.length, out = [];
      for (var i = 0; i < n; i++) out.push(this.binop(op, Array.isArray(a) ? a[i] : a, Array.isArray(b) ? b[i] : b));
      return out;
    }
    if (op === '&') { if (isErr(a)) return a; if (isErr(b)) return b; return toStr(a) + toStr(b); }
    if (/^(=|<>|<|>|<=|>=)$/.test(op)) {
      if (isErr(a)) return a; if (isErr(b)) return b;
      var k = compare(a, b);
      return op === '=' ? k === 0 : op === '<>' ? k !== 0 : op === '<' ? k < 0 : op === '>' ? k > 0 : op === '<=' ? k <= 0 : k >= 0;
    }
    var x = toNum(a), y = toNum(b);
    if (isErr(x)) return x; if (isErr(y)) return y;
    switch (op) {
      case '+': return x + y;
      case '-': return x - y;
      case '*': return x * y;
      case '/': return y === 0 ? ERR.DIV0 : x / y;
      case '^': { var z = Math.pow(x, y); return isFinite(z) ? z : ERR.NUM; }
    }
    return ERR.VALUE;
  };
  W.nums = function (args, s, r, c) {  // numbers from arguments; ranges skip text and blanks (Excel rule)
    var out = [];
    for (var i = 0; i < args.length; i++) {
      var v = this.ev(args[i], s, r, c);
      if (v instanceof Range) {
        var vals = this.values(v);
        for (var j = 0; j < vals.length; j++) { if (isErr(vals[j])) return vals[j]; if (typeof vals[j] === 'number') out.push(vals[j]); }
      } else if (Array.isArray(v)) {
        for (var q = 0; q < v.length; q++) if (typeof v[q] === 'number') out.push(v[q]);
      } else { var n = toNum(v); if (isErr(n)) return n; out.push(n); }
    }
    return out;
  };
  W.call = function (fn, args, s, r, c) {
    var self = this;
    function arg(i) { return self.deref(self.ev(args[i], s, r, c)); }
    function num(i) { return toNum(arg(i)); }
    switch (fn) {
      case 'IF': {
        var t = toBool(arg(0));
        if (isErr(t)) return t;
        if (t) return args.length > 1 ? arg(1) : true;
        return args.length > 2 ? arg(2) : false;
      }
      case 'AND': case 'OR': {
        var res = fn === 'AND';
        for (var i = 0; i < args.length; i++) {
          var b = toBool(arg(i)); if (isErr(b)) return b;
          res = fn === 'AND' ? (res && b) : (res || b);
        }
        return res;
      }
      case 'PI': return Math.PI;
      case 'TODAY': return this.today;
      case 'SQRT': { var x = num(0); if (isErr(x)) return x; return x < 0 ? ERR.NUM : Math.sqrt(x); }
      case 'EXP': { var e = num(0); return isErr(e) ? e : Math.exp(e); }
      case 'ABS': { var a = num(0); return isErr(a) ? a : Math.abs(a); }
      case 'ROUND': {
        var v = num(0), d = num(1); if (isErr(v)) return v; if (isErr(d)) return d;
        var f = Math.pow(10, d); return Math.sign(v) * Math.round(Math.abs(v) * f + 1e-9) / f;
      }
      case 'FLOOR': {
        var fv = num(0), sg = num(1); if (isErr(fv)) return fv; if (isErr(sg)) return sg;
        if (sg === 0) return 0; return Math.floor(fv / sg + 1e-12) * sg;
      }
      case 'MAX': case 'MIN': case 'SUM': {
        var ns = this.nums(args, s, r, c); if (isErr(ns)) return ns;
        if (fn === 'SUM') return ns.reduce(function (p, q) { return p + q; }, 0);
        if (!ns.length) return 0;
        return fn === 'MAX' ? Math.max.apply(null, ns) : Math.min.apply(null, ns);
      }
      case 'SUMPRODUCT': {
        var arrays = args.map(function (a) { var v = self.arr(self.ev(a, s, r, c)); return Array.isArray(v) ? v : [v]; });
        var total = 0;
        for (var k = 0; k < arrays[0].length; k++) {
          var p = 1;
          for (var m = 0; m < arrays.length; m++) {
            var val = arrays[m][k];
            if (isErr(val)) return val;
            p *= typeof val === 'number' ? val : typeof val === 'boolean' ? 0 : 0;
          }
          total += p;
        }
        return total;
      }
      case 'INDEX': {
        var rg = this.ev(args[0], s, r, c);
        var ix = num(1); if (isErr(ix)) return ix;
        if (!(rg instanceof Range)) return ix === 1 ? rg : ERR.REF;
        var vals = this.values(rg);
        if (args.length > 2) {
          var col = num(2), w = rg.c2 - rg.c1 + 1;
          return this.cell(rg.s, rg.r1 + ix - 1, rg.c1 + (col || 1) - 1) ;
        }
        if (ix < 1 || ix > vals.length) return ERR.REF;
        return vals[ix - 1];
      }
      case 'MATCH': {
        var look = arg(0), mr = this.ev(args[1], s, r, c);
        if (isErr(look)) return look;
        var list = mr instanceof Range ? this.values(mr) : [mr];
        for (var z = 0; z < list.length; z++) {
          var li = list[z];
          if (li === null || li === undefined || li === '') continue;
          if (compare(li, look) === 0 && typeof li === typeof look) return z + 1;
        }
        return ERR.NA;
      }
      case 'MINIFS': {
        var minv = this.values(this.ev(args[0], s, r, c)), best = null;
        var tests = [];
        for (var t2 = 1; t2 < args.length; t2 += 2) tests.push([this.values(this.ev(args[t2], s, r, c)), criterion(arg(t2 + 1))]);
        for (var q = 0; q < minv.length; q++) {
          if (typeof minv[q] !== 'number') continue;
          var ok = true;
          for (var u = 0; u < tests.length && ok; u++) ok = tests[u][1](tests[u][0][q]);
          if (ok && (best === null || minv[q] < best)) best = minv[q];
        }
        return best === null ? 0 : best;
      }
      case 'COUNTIF': {
        var cv = this.values(this.ev(args[0], s, r, c)), test = criterion(arg(1)), cnt = 0;
        for (var y = 0; y < cv.length; y++) if (test(cv[y])) cnt++;
        return cnt;
      }
      case 'TEXT': { var tv = arg(0); if (isErr(tv)) return tv; return format(tv, toStr(arg(1))); }
      case 'TEXTJOIN': {
        var delim = toStr(arg(0)), ignore = toBool(arg(1)), parts = [];
        for (var g = 2; g < args.length; g++) {
          var gv = this.arr(this.ev(args[g], s, r, c));
          (Array.isArray(gv) ? gv : [gv]).forEach(function (x) {
            if (isErr(x)) { parts.push(x.code); return; }
            var st = toStr(x); if (!(ignore && st === '')) parts.push(st);
          });
        }
        return parts.join(delim);
      }
      case 'LOWER': { var lv = arg(0); return isErr(lv) ? lv : toStr(lv).toLowerCase(); }
    }
    return ERR.NAME;
  };
  W.name = function (n) {  // value of a single-cell defined name
    var rg = this.nameRange(n);
    if (isErr(rg)) return rg;
    return this.cell(rg.s, rg.r1, rg.c1);
  };

  var api = { Workbook: Workbook, parse: parse, tokenize: tokenize, format: format, isErr: isErr, XLError: XLError };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.xlcalc = api;
})(this);
