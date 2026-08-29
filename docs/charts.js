/* 依存ゼロの軽量SVGチャート。dataviz規約に沿って:
   - 細いマーク / データ端4px角丸 / 線2px / ホバー時マーカー>=8px
   - 2系列以上は必ず凡例、4系列以下は直接ラベルも付ける
   - すべてのチャートに表ビュー(details)を併設
   - 系列色はエンティティ固定（並び替えで色が入れ替わらない） */
'use strict';

const NS = 'http://www.w3.org/2000/svg';
const SERIES = ['--series-1','--series-2','--series-3','--series-4',
                '--series-5','--series-6','--series-7','--series-8'];

export function cssVar(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
export function esc(s) {
  return String(s == null ? '' : s).replace(/[&<>"']/g,
    c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function el(tag, attrs, parent) {
  const n = document.createElementNS(NS, tag);
  for (const k in attrs) if (attrs[k] != null) n.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(n);
  return n;
}
let _measure;
function textWidth(s, font) {
  if (!_measure) _measure = document.createElement('canvas').getContext('2d');
  _measure.font = font;
  return _measure.measureText(s).width;
}

/* ---------------- tooltip ---------------- */
let tip;
function tipEl() {
  if (!tip) {
    tip = document.createElement('div');
    tip.className = 'tooltip';
    tip.setAttribute('role', 'status');
    document.body.appendChild(tip);
  }
  return tip;
}
function showTip(html, x, y) {
  const t = tipEl();
  t.innerHTML = html;
  t.style.opacity = '1';
  const r = t.getBoundingClientRect();
  let left = x + 14, top = y + 14;
  if (left + r.width > innerWidth - 8) left = x - r.width - 14;
  if (top + r.height > innerHeight - 8) top = y - r.height - 14;
  t.style.left = Math.max(8, left) + 'px';
  t.style.top = Math.max(8, top) + 'px';
}
function hideTip() { if (tip) tip.style.opacity = '0'; }

/* ---------------- shared helpers ---------------- */
function mount(host, render) {
  const draw = () => {
    const w = host.clientWidth;
    if (w > 0) { host.innerHTML = ''; render(host, w); }
  };
  draw();
  host.__draw = draw;
  if (typeof ResizeObserver !== 'undefined') {
    let last = host.clientWidth;
    new ResizeObserver(() => {
      if (Math.abs(host.clientWidth - last) > 2) { last = host.clientWidth; draw(); }
    }).observe(host);
  }
  const mq = matchMedia('(prefers-color-scheme: dark)');
  mq.addEventListener('change', draw);
  return draw;
}
/* 右端だけ4pxの角丸にした横バー（ベースラインに接地させる） */
function barPathRight(x, y, w, h, r) {
  r = Math.max(0, Math.min(r, w, h / 2));
  return `M${x},${y}h${w - r}a${r},${r} 0 0 1 ${r},${r}v${h - 2 * r}` +
         `a${r},${r} 0 0 1 ${-r},${r}h${-(w - r)}z`;
}
/* 上端だけ角丸の縦バー */
function barPathUp(x, y, w, h, r) {
  r = Math.max(0, Math.min(r, h, w / 2));
  return `M${x},${y + h}v${-(h - r)}a${r},${r} 0 0 1 ${r},${-r}h${w - 2 * r}` +
         `a${r},${r} 0 0 1 ${r},${r}v${h - r}z`;
}
function tableView(host, headers, rows, label) {
  const d = document.createElement('details');
  d.className = 'table-view';
  const cells = rows.map(r =>
    '<tr>' + r.map((c, i) =>
      `<td${i ? ' class="num"' : ''}>${esc(c)}</td>`).join('') + '</tr>').join('');
  d.innerHTML = `<summary>${esc(label || '数値を表で見る')}</summary>` +
    `<table class="data"><thead><tr>` +
    headers.map((h, i) => `<th${i ? ' class="num"' : ''}>${esc(h)}</th>`).join('') +
    `</tr></thead><tbody>${cells}</tbody></table>`;
  host.appendChild(d);
}

/* ---------------- 横棒（単一系列） ---------------- */
export function hbar(host, opt) {
  const data = opt.data.slice(0, opt.limit || 20);
  if (!data.length) { host.innerHTML = '<p class="note">データがありません</p>'; return; }
  const wrapEl = document.createElement('div');
  wrapEl.className = 'chart-scroll';
  host.appendChild(wrapEl);

  mount(wrapEl, (h, W) => {
    const rowH = 26, padT = 6, padB = 4;
    const font = '12px ' + getComputedStyle(document.body).fontFamily;
    const nameW = Math.min(220, Math.max(70,
      Math.max(...data.map(d => textWidth(d.name, font))) + 12));
    const valFont = '11px ' + getComputedStyle(document.body).fontFamily;
    const valW = Math.max(...data.map(d =>
      textWidth(opt.fmt ? opt.fmt(d.value) : String(d.value), valFont))) + 12;
    const H = padT + data.length * rowH + padB;
    const x0 = nameW, x1 = Math.max(x0 + 40, W - valW);
    const max = Math.max(...data.map(d => d.value)) || 1;
    const color = cssVar(opt.color || '--series-1');
    const surface = cssVar('--surface-1');

    const svg = el('svg', { class: 'chart', width: W, height: H,
      viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': opt.aria || 'horizontal bar chart' }, h);
    el('line', { class: 'axis-line', x1: x0 - .5, y1: padT, x2: x0 - .5, y2: H - padB }, svg);

    data.forEach((d, i) => {
      const y = padT + i * rowH, bh = 14, by = y + (rowH - bh) / 2;
      const bw = Math.max(2, (d.value / max) * (x1 - x0 - 4));
      const g = el('g', { tabindex: '0', role: 'listitem' }, svg);
      el('rect', { x: x0, y, width: Math.max(0, W - x0), height: rowH,
        fill: 'transparent' }, g);
      el('path', { d: barPathRight(x0, by, bw, bh, 4), fill: color,
        stroke: surface, 'stroke-width': 2, 'paint-order': 'stroke' }, g);
      const tn = el('text', { class: 'bar-name', x: x0 - 8, y: y + rowH / 2 + 4,
        'text-anchor': 'end' }, g);
      tn.textContent = d.name;
      const tv = el('text', { class: 'bar-value', x: x0 + bw + 7,
        y: y + rowH / 2 + 4 }, g);
      tv.textContent = opt.fmt ? opt.fmt(d.value) : d.value;

      const body = `<div class="tt-h">${esc(d.name)}</div>` +
        (d.cat ? `<div class="tt-r">${esc(d.cat)}</div>` : '') +
        `<div class="tt-r"><span class="swatch" style="background:${color}"></span>` +
        `${esc(opt.valueLabel || '件数')}<b>${esc(opt.fmt ? opt.fmt(d.value) : d.value)}</b></div>` +
        (d.note ? `<div class="tt-r">${esc(d.note)}</div>` : '');
      const move = e => showTip(body, e.clientX, e.clientY);
      g.addEventListener('pointermove', move);
      g.addEventListener('pointerenter', move);
      g.addEventListener('pointerleave', hideTip);
      g.addEventListener('focus', () => {
        const r = g.getBoundingClientRect();
        showTip(body, r.left + 40, r.top);
      });
      g.addEventListener('blur', hideTip);
    });
  });

  tableView(host, [opt.nameLabel || '項目', opt.valueLabel || '件数'],
    data.map(d => [d.cat ? `${d.name}（${d.cat}）` : d.name,
                   opt.fmt ? opt.fmt(d.value) : d.value]));
}

/* ---------------- 折れ線（複数系列・クロスヘア） ---------------- */
export function multiline(host, opt) {
  const labels = opt.labels;
  const series = opt.series.map((s, i) => ({
    ...s, color: cssVar(SERIES[i % SERIES.length]), on: true,
  }));
  if (!labels.length) { host.innerHTML = '<p class="note">データがありません</p>'; return; }

  const legend = document.createElement('ul');
  legend.className = 'legend';
  host.appendChild(legend);
  const wrapEl = document.createElement('div');
  wrapEl.className = 'chart-scroll';
  host.appendChild(wrapEl);

  let redraw = () => {};
  series.forEach(s => {
    const li = document.createElement('li');
    const b = document.createElement('button');
    b.type = 'button';
    b.setAttribute('aria-pressed', 'true');
    b.innerHTML = `<span class="swatch" style="background:${s.color}"></span>${esc(s.name)}`;
    b.addEventListener('click', () => {
      s.on = !s.on;
      b.setAttribute('aria-pressed', String(s.on));
      redraw();
    });
    li.appendChild(b);
    legend.appendChild(li);
  });

  redraw = mount(wrapEl, (h, W) => {
    const on = series.filter(s => s.on);
    const H = opt.height || 260;
    const padL = 34, padR = on.length && on.length <= 4 ? 96 : 14,
          padT = 12, padB = 30;
    const iw = Math.max(30, W - padL - padR), ih = H - padT - padB;
    const max = Math.max(1, ...on.flatMap(s => s.values));
    const yMax = Math.ceil(max * 1.12) || 1;
    const X = i => padL + (labels.length === 1 ? iw / 2
      : (i / (labels.length - 1)) * iw);
    const Y = v => padT + ih - (v / yMax) * ih;
    const surface = cssVar('--surface-1');

    const svg = el('svg', { class: 'chart', width: W, height: H,
      viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': opt.aria || 'line chart' }, h);

    const ticks = 4;
    for (let t = 0; t <= ticks; t++) {
      const v = Math.round((yMax / ticks) * t), y = Y(v);
      el('line', { class: 'tick-line', x1: padL, y1: y, x2: padL + iw, y2: y }, svg);
      const tx = el('text', { class: 'axis-label', x: padL - 7, y: y + 4,
        'text-anchor': 'end' }, svg);
      tx.textContent = v;
    }
    const every = Math.max(1, Math.ceil(labels.length / Math.floor(iw / 62)));
    labels.forEach((lb, i) => {
      if (i % every && i !== labels.length - 1) return;
      const tx = el('text', { class: 'axis-label', x: X(i), y: H - 10,
        'text-anchor': 'middle' }, svg);
      tx.textContent = opt.tickFmt ? opt.tickFmt(lb) : lb;
    });
    el('line', { class: 'axis-line', x1: padL, y1: padT + ih,
      x2: padL + iw, y2: padT + ih }, svg);

    const cross = el('line', { class: 'tick-line', x1: 0, y1: padT, x2: 0,
      y2: padT + ih, stroke: cssVar('--border-strong'), opacity: 0 }, svg);

    on.forEach(s => {
      el('path', {
        d: s.values.map((v, i) => `${i ? 'L' : 'M'}${X(i)},${Y(v)}`).join(''),
        fill: 'none', stroke: s.color, 'stroke-width': 2,
        'stroke-linecap': 'round', 'stroke-linejoin': 'round',
      }, svg);
    });
    if (on.length && on.length <= 4) {
      on.forEach(s => {
        const t = el('text', { x: padL + iw + 8, y: Y(s.values[s.values.length - 1]) + 4,
          fill: s.color, 'font-size': 12, 'font-weight': 600 }, svg);
        t.textContent = s.name;
      });
    }

    const dots = on.map(s => el('circle', { r: 4.5, fill: s.color,
      stroke: surface, 'stroke-width': 2, opacity: 0 }, svg));

    const hit = el('rect', { x: padL, y: padT, width: iw, height: ih,
      fill: 'transparent' }, svg);
    const at = e => {
      const r = svg.getBoundingClientRect();
      const px = (e.clientX - r.left) * (W / r.width);
      let i = labels.length === 1 ? 0
        : Math.round(((px - padL) / iw) * (labels.length - 1));
      i = Math.max(0, Math.min(labels.length - 1, i));
      cross.setAttribute('x1', X(i)); cross.setAttribute('x2', X(i));
      cross.setAttribute('opacity', 1);
      on.forEach((s, k) => {
        dots[k].setAttribute('cx', X(i));
        dots[k].setAttribute('cy', Y(s.values[i]));
        dots[k].setAttribute('opacity', 1);
      });
      const rows = on.slice()
        .sort((a, b) => b.values[i] - a.values[i])
        .map(s => `<div class="tt-r"><span class="swatch" style="background:${s.color}"></span>` +
          `${esc(s.name)}<b>${s.values[i]}</b></div>`).join('');
      showTip(`<div class="tt-h">${esc(labels[i])}</div>${rows}`, e.clientX, e.clientY);
    };
    hit.addEventListener('pointermove', at);
    hit.addEventListener('pointerenter', at);
    hit.addEventListener('pointerleave', () => {
      hideTip(); cross.setAttribute('opacity', 0);
      dots.forEach(d => d.setAttribute('opacity', 0));
    });
  });
  tableView(host, [opt.xLabel || '週', ...opt.series.map(s => s.name)],
    labels.map((lb, i) => [lb, ...opt.series.map(s => s.values[i])]));
}

/* ---------------- 発散バー（増減） ---------------- */
export function divbar(host, opt) {
  const data = opt.data.filter(d => d.delta !== 0).slice(0, opt.limit || 12);
  if (!data.length) { host.innerHTML = '<p class="note">増減が出るだけの週数がまだありません</p>'; return; }
  const wrapEl = document.createElement('div');
  wrapEl.className = 'chart-scroll';
  host.appendChild(wrapEl);

  mount(wrapEl, (h, W) => {
    const rowH = 26, padT = 6, padB = 4;
    const font = '12px ' + getComputedStyle(document.body).fontFamily;
    const nameW = Math.min(200, Math.max(70,
      Math.max(...data.map(d => textWidth(d.name, font))) + 12));
    const H = padT + data.length * rowH + padB;
    const mid = nameW + (W - nameW) / 2;
    const half = (W - nameW) / 2 - 34;
    const max = Math.max(...data.map(d => Math.abs(d.delta))) || 1;
    const pos = cssVar('--diverge-pos'), neg = cssVar('--diverge-neg');
    const surface = cssVar('--surface-1');

    const svg = el('svg', { class: 'chart', width: W, height: H,
      viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': opt.aria || 'diverging bar chart' }, h);
    el('line', { class: 'axis-line', x1: mid, y1: padT, x2: mid, y2: H - padB }, svg);

    data.forEach((d, i) => {
      const y = padT + i * rowH, bh = 14, by = y + (rowH - bh) / 2;
      const bw = Math.max(2, (Math.abs(d.delta) / max) * half);
      const up = d.delta > 0;
      const g = el('g', { tabindex: '0' }, svg);
      el('rect', { x: 0, y, width: W, height: rowH, fill: 'transparent' }, g);
      const p = up ? barPathRight(mid, by, bw, bh, 4)
        : barPathRight(mid - bw, by, bw, bh, 4);
      el('path', { d: p, fill: up ? pos : neg, stroke: surface,
        'stroke-width': 2, 'paint-order': 'stroke',
        transform: up ? null : `rotate(180 ${mid - bw / 2} ${by + bh / 2})` }, g);
      const tn = el('text', { class: 'bar-name', x: nameW - 10,
        y: y + rowH / 2 + 4, 'text-anchor': 'end' }, g);
      tn.textContent = d.name;
      const tv = el('text', { class: 'bar-value',
        x: up ? mid + bw + 7 : mid - bw - 7, y: y + rowH / 2 + 4,
        'text-anchor': up ? 'start' : 'end' }, g);
      tv.textContent = (up ? '+' : '') + d.delta;

      const body = `<div class="tt-h">${esc(d.name)}</div>` +
        `<div class="tt-r">直近${opt.window || 4}週<b>${d.recent}</b></div>` +
        `<div class="tt-r">その前${opt.window || 4}週<b>${d.prev}</b></div>` +
        `<div class="tt-r">増減<b>${(up ? '+' : '') + d.delta}</b></div>`;
      const move = e => showTip(body, e.clientX, e.clientY);
      g.addEventListener('pointermove', move);
      g.addEventListener('pointerenter', move);
      g.addEventListener('pointerleave', hideTip);
    });
  });

  tableView(host, ['技術', '直近', '前期', '増減'],
    data.map(d => [d.name, d.recent, d.prev, (d.delta > 0 ? '+' : '') + d.delta]));
}

/* ---------------- 縦棒ヒストグラム ---------------- */
export function vbar(host, opt) {
  const data = opt.data;
  if (!data.length || data.every(d => !d.value)) {
    host.innerHTML = '<p class="note">' +
      esc(opt.empty || 'データがありません') + '</p>';
    return;
  }
  const wrapEl = document.createElement('div');
  wrapEl.className = 'chart-scroll';
  host.appendChild(wrapEl);

  mount(wrapEl, (h, W) => {
    const H = opt.height || 220;
    const padL = 34, padR = 10, padT = 12, padB = 34;
    const iw = Math.max(30, W - padL - padR), ih = H - padT - padB;
    const max = Math.max(...data.map(d => d.value)) || 1;
    const yMax = Math.ceil(max * 1.12) || 1;
    const slot = iw / data.length, bw = Math.max(4, Math.min(52, slot - 8));
    const color = cssVar(opt.color || '--series-1');
    const surface = cssVar('--surface-1');

    const svg = el('svg', { class: 'chart', width: W, height: H,
      viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': opt.aria || 'bar chart' }, h);
    for (let t = 0; t <= 4; t++) {
      const v = Math.round((yMax / 4) * t), y = padT + ih - (v / yMax) * ih;
      el('line', { class: 'tick-line', x1: padL, y1: y, x2: padL + iw, y2: y }, svg);
      const tx = el('text', { class: 'axis-label', x: padL - 7, y: y + 4,
        'text-anchor': 'end' }, svg);
      tx.textContent = v;
    }
    el('line', { class: 'axis-line', x1: padL, y1: padT + ih,
      x2: padL + iw, y2: padT + ih }, svg);

    data.forEach((d, i) => {
      const cx = padL + slot * i + slot / 2;
      const bh = (d.value / yMax) * ih;
      const g = el('g', { tabindex: '0' }, svg);
      el('rect', { x: cx - slot / 2, y: padT, width: slot, height: ih,
        fill: 'transparent' }, g);
      el('path', { d: barPathUp(cx - bw / 2, padT + ih - bh, bw, bh, 4),
        fill: color, stroke: surface, 'stroke-width': 2,
        'paint-order': 'stroke' }, g);
      const tx = el('text', { class: 'axis-label', x: cx, y: H - 12,
        'text-anchor': 'middle' }, g);
      tx.textContent = d.name;
      const body = `<div class="tt-h">${esc(d.name)}</div>` +
        `<div class="tt-r"><span class="swatch" style="background:${color}"></span>` +
        `${esc(opt.valueLabel || '件数')}<b>${d.value}</b></div>`;
      const move = e => showTip(body, e.clientX, e.clientY);
      g.addEventListener('pointermove', move);
      g.addEventListener('pointerenter', move);
      g.addEventListener('pointerleave', hideTip);
    });
  });

  tableView(host, [opt.nameLabel || '区分', opt.valueLabel || '件数'],
    data.map(d => [d.name, d.value]));
}

/* ---------------- 3D散布図（マウスドラッグで視点回転） ----------------
   業界 × ロール × 技術領域 の3軸。外部ライブラリ非依存。
   奥行きは、床への垂線・遠近・重なり順で読ませる。
   3D単体では正確な値が読めないので、ホバーの数値と表ビューを必ず併設する。 */
export function scatter3d(host, opt) {
  const cube = opt.cube;
  if (!cube || !cube.cells.length) {
    host.innerHTML = '<p class="note">3次元集計のデータがありません</p>';
    return;
  }
  const AX = { x: cube.positions, y: cube.industries, z: cube.categories };

  const bar = document.createElement('div');
  bar.className = 'filters';
  bar.innerHTML =
    '<button type="button" id="d3-reset" class="btn3d">視点をリセット</button>' +
    '<label class="lbl3d">最小件数 <input id="d3-min" type="range" min="1" max="12" value="1">' +
    '<b id="d3-minv">1</b></label>' +
    '<span class="count" id="d3-count"></span>';
  host.appendChild(bar);

  const wrapEl = document.createElement('div');
  wrapEl.className = 'chart-scroll';
  host.appendChild(wrapEl);

  const hint = document.createElement('p');
  hint.className = 'note';
  hint.style.marginTop = '10px';
  hint.textContent =
    'ドラッグで視点を回転、ホイールで拡大縮小。点にカーソルを合わせると内訳が出ます。'
    + '（キーボード操作: フォーカス後に矢印キーで回転）';
  host.appendChild(hint);

  const view = { az: -0.62, el: 0.42, zoom: 1 };
  const state = { min: 1 };
  let W = 0, H = opt.height || 520, raf = 0, hot = -1;

  const svg = el('svg', {
    class: 'chart', role: 'img', tabindex: '0',
    'aria-label': opt.aria || '業界・ロール・技術領域の3次元散布図',
  });
  svg.style.touchAction = 'none';
  svg.style.cursor = 'grab';
  wrapEl.appendChild(svg);

  const project = (p) => {
    const ca = Math.cos(view.az), sa = Math.sin(view.az);
    const ce = Math.cos(view.el), se = Math.sin(view.el);
    const xa = p[0] * ca - p[1] * sa;
    const ya = p[0] * sa + p[1] * ca;
    const za = p[2];
    const depth = ya * ce + za * se;          // 大きいほど手前
    const sx = xa;
    const sy = -(za * ce - ya * se);
    const persp = 1 / (1 - depth * 0.16);
    const k = 0.34 * Math.min(W, H) * view.zoom * persp;
    return { x: W / 2 + sx * k, y: H / 2 + sy * k, d: depth, k };
  };
  const gridPos = (i, n) => (n <= 1 ? 0 : (i / (n - 1)) * 2 - 1);

  function draw() {
    raf = 0;
    if (!W) return;
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    svg.setAttribute('width', W);
    svg.setAttribute('height', H);
    svg.setAttribute('viewBox', `0 0 ${W} ${H}`);

    const line = cssVar('--grid');
    const axisC = cssVar('--border-strong');
    const surface = cssVar('--surface-1');
    const muted = cssVar('--text-muted');
    const ramp = ['--seq-100', '--seq-250', '--seq-450', '--seq-600'].map(cssVar);

    // 床グリッド（z = -1 の面）
    const nx = AX.x.length, ny = AX.y.length;
    for (let i = 0; i < nx; i++) {
      const a = project([gridPos(i, nx), -1, -1]);
      const b = project([gridPos(i, nx), 1, -1]);
      el('line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: line, 'stroke-width': 1 }, svg);
    }
    for (let j = 0; j < ny; j++) {
      const a = project([-1, gridPos(j, ny), -1]);
      const b = project([1, gridPos(j, ny), -1]);
      el('line', { x1: a.x, y1: a.y, x2: b.x, y2: b.y, stroke: line, 'stroke-width': 1 }, svg);
    }
    // 縦軸
    const zc = project([-1, -1, -1]), zt = project([-1, -1, 1]);
    el('line', { x1: zc.x, y1: zc.y, x2: zt.x, y2: zt.y, stroke: axisC, 'stroke-width': 1 }, svg);

    // 軸ラベル
    const label = (p, text, anchor, color, size) => {
      const q = project(p);
      const t = el('text', {
        x: q.x, y: q.y, 'text-anchor': anchor || 'middle',
        fill: color || muted, 'font-size': size || 10.5,
        'dominant-baseline': 'middle',
      }, svg);
      t.textContent = text;
    };
    AX.x.forEach((n, i) => label([gridPos(i, nx), -1.18, -1], n, 'middle'));
    AX.y.forEach((n, j) => label([1.2, gridPos(j, ny), -1], n, 'start'));
    AX.z.forEach((n, k) => label([-1.14, -1.14, gridPos(k, AX.z.length)], n, 'end'));
    label([0, -1.55, -1], 'ロール', 'middle', cssVar('--text-secondary'), 12);
    label([1.6, 0, -1], '業界', 'start', cssVar('--text-secondary'), 12);
    label([-1.1, -1.1, 1.3], '技術領域', 'end', cssVar('--text-secondary'), 12);

    // 点（奥から手前へ描く）
    const pts = cube.cells
      .filter((c) => c.n >= state.min)
      .map((c) => {
        const p = [gridPos(c.p, nx), gridPos(c.i, ny), gridPos(c.c, AX.z.length)];
        const s = project(p);
        const foot = project([p[0], p[1], -1]);
        const t = cube.max > 1 ? (c.n - 1) / (cube.max - 1) : 1;
        return { c, s, foot, t, r: (4 + Math.sqrt(t) * 15) * view.zoom };
      })
      .sort((a, b) => a.s.d - b.s.d);

    bar.querySelector('#d3-count').textContent =
      `${pts.length} / ${cube.cells.length} 組み合わせ`;

    pts.forEach((q) => {
      el('line', {
        x1: q.s.x, y1: q.s.y, x2: q.foot.x, y2: q.foot.y,
        stroke: line, 'stroke-width': 1,
      }, svg);
    });
    pts.forEach((q, idx) => {
      const fill = ramp[Math.min(ramp.length - 1, Math.floor(q.t * ramp.length))];
      el('circle', {
        cx: q.s.x, cy: q.s.y, r: q.r,
        fill, stroke: idx === hot ? cssVar('--text-primary') : surface,
        'stroke-width': idx === hot ? 3 : 2,
        opacity: 0.55 + 0.45 * ((q.s.d + 1.8) / 3.6),
      }, svg);
    });
    svg.__pts = pts;
  }

  const schedule = () => { if (!raf) raf = requestAnimationFrame(draw); };

  // --- 操作 ---
  let drag = null;
  svg.addEventListener('pointerdown', (e) => {
    drag = { x: e.clientX, y: e.clientY, az: view.az, el: view.el };
    svg.setPointerCapture(e.pointerId);
    svg.style.cursor = 'grabbing';
    hideTip();
  });
  svg.addEventListener('pointermove', (e) => {
    if (drag) {
      view.az = drag.az + (e.clientX - drag.x) * 0.0085;
      view.el = Math.max(-1.35, Math.min(1.35, drag.el - (e.clientY - drag.y) * 0.0085));
      schedule();
      return;
    }
    const r = svg.getBoundingClientRect();
    const mx = (e.clientX - r.left) * (W / r.width);
    const my = (e.clientY - r.top) * (H / r.height);
    const pts = svg.__pts || [];
    let best = -1, bestD = 1e9;
    for (let i = pts.length - 1; i >= 0; i--) {
      const q = pts[i];
      const d = Math.hypot(q.s.x - mx, q.s.y - my);
      if (d < Math.max(q.r, 9) && d < bestD) { bestD = d; best = i; }
    }
    if (best !== hot) { hot = best; schedule(); }
    if (best >= 0) {
      const c = pts[best].c;
      showTip(
        `<div class="tt-h">${esc(AX.y[c.i])} × ${esc(AX.x[c.p])}</div>` +
        `<div class="tt-r">技術領域<b>${esc(AX.z[c.c])}</b></div>` +
        `<div class="tt-r">案件数<b>${c.n}</b></div>`,
        e.clientX, e.clientY);
    } else hideTip();
  });
  const endDrag = (e) => {
    if (!drag) return;
    drag = null;
    svg.style.cursor = 'grab';
    if (e && e.pointerId != null && svg.hasPointerCapture(e.pointerId)) {
      svg.releasePointerCapture(e.pointerId);
    }
  };
  svg.addEventListener('pointerup', endDrag);
  svg.addEventListener('pointercancel', endDrag);
  svg.addEventListener('pointerleave', () => { hideTip(); hot = -1; schedule(); });
  svg.addEventListener('wheel', (e) => {
    e.preventDefault();
    view.zoom = Math.max(0.55, Math.min(2.4, view.zoom * (e.deltaY > 0 ? 0.92 : 1.08)));
    schedule();
  }, { passive: false });
  svg.addEventListener('keydown', (e) => {
    const step = 0.09;
    if (e.key === 'ArrowLeft') view.az -= step;
    else if (e.key === 'ArrowRight') view.az += step;
    else if (e.key === 'ArrowUp') view.el = Math.min(1.35, view.el + step);
    else if (e.key === 'ArrowDown') view.el = Math.max(-1.35, view.el - step);
    else if (e.key === '+' || e.key === '=') view.zoom = Math.min(2.4, view.zoom * 1.1);
    else if (e.key === '-') view.zoom = Math.max(0.55, view.zoom / 1.1);
    else return;
    e.preventDefault();
    schedule();
  });
  bar.querySelector('#d3-reset').addEventListener('click', () => {
    view.az = -0.62; view.el = 0.42; view.zoom = 1; schedule();
  });
  bar.querySelector('#d3-min').addEventListener('input', (e) => {
    state.min = +e.target.value;
    bar.querySelector('#d3-minv').textContent = state.min;
    schedule();
  });

  const resize = () => {
    const w = wrapEl.clientWidth;
    if (w > 0 && Math.abs(w - W) > 2) { W = w; schedule(); }
  };
  resize();
  if (typeof ResizeObserver !== 'undefined') new ResizeObserver(resize).observe(wrapEl);
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', schedule);

  tableView(host,
    ['業界', 'ロール', '技術領域', '案件数'],
    cube.cells.slice().sort((a, b) => b.n - a.n).slice(0, 60)
      .map((c) => [AX.y[c.i], AX.x[c.p], AX.z[c.c], c.n]),
    '数値を表で見る（上位60組み合わせ）');
}

/* ---------------- 需要量 × モメンタム の2軸マップ ----------------
   4象限に切って「新興・急伸」を見つけるための散布図。
   色は象限（＝意思決定上の意味）に対応させ、ランクには対応させない。 */
export function quadrant(host, opt) {
  const pts = opt.points;
  if (!pts.length) { host.innerHTML = '<p class="note">データがありません</p>'; return; }

  const legend = document.createElement('ul');
  legend.className = 'legend';
  host.appendChild(legend);
  const wrapEl = document.createElement('div');
  wrapEl.className = 'chart-scroll';
  host.appendChild(wrapEl);

  const GROUPS = [
    { key: 'rising', name: '新興・急伸（狙い目）', v: '--series-3' },
    { key: 'core', name: '主力（伸びている大領域）', v: '--series-1' },
    { key: 'flat', name: '横ばい・後退', v: '--text-muted' },
  ];

  mount(wrapEl, (h, W) => {
    const H = opt.height || 420;
    const padL = 56, padR = 24, padT = 18, padB = 46;
    const iw = Math.max(60, W - padL - padR), ih = H - padT - padB;
    const xs = pts.map(p => p.x), ys = pts.map(p => p.y);
    const xMax = Math.max(...xs) * 1.06 || 1;
    const yMax = Math.max(...ys, 1), yMin = Math.min(...ys, -1);
    const pad = (yMax - yMin) * 0.12;
    const yHi = yMax + pad, yLo = yMin - pad;
    const X = v => padL + (v / xMax) * iw;
    const Y = v => padT + ((yHi - v) / (yHi - yLo)) * ih;
    const xMid = opt.xMid != null ? opt.xMid
      : xs.slice().sort((a, b) => a - b)[Math.floor(xs.length / 2)];
    const maxSize = Math.max(...pts.map(p => p.size || 1)) || 1;

    const grid = cssVar('--grid'), axis = cssVar('--border-strong');
    const surface = cssVar('--surface-1'), muted = cssVar('--text-muted');
    const color = Object.fromEntries(GROUPS.map(g => [g.key, cssVar(g.v)]));

    const svg = el('svg', { class: 'chart', width: W, height: H,
      viewBox: `0 0 ${W} ${H}`, role: 'img',
      'aria-label': opt.aria || 'demand versus momentum scatter' }, h);

    // 「新興・急伸」象限を面で示す
    el('rect', { x: padL, y: padT, width: Math.max(0, X(xMid) - padL),
      height: Math.max(0, Y(0) - padT), fill: color.rising, opacity: 0.09 }, svg);
    const bl = el('text', { x: padL + 12, y: padT + 18, fill: color.rising,
      'font-size': 11.5, 'font-weight': 600 }, svg);
    bl.textContent = opt.bandLabel || '新興・急伸 — 先回りして取るべき領域';

    el('line', { x1: padL, y1: Y(0), x2: padL + iw, y2: Y(0),
      stroke: axis, 'stroke-width': 1, 'stroke-dasharray': '4 4' }, svg);
    el('line', { x1: X(xMid), y1: padT, x2: X(xMid), y2: padT + ih,
      stroke: grid, 'stroke-width': 1, 'stroke-dasharray': '4 4' }, svg);
    el('line', { x1: padL, y1: padT, x2: padL, y2: padT + ih,
      stroke: axis, 'stroke-width': 1 }, svg);

    [yHi, 0, yLo].forEach(v => {
      const t = el('text', { class: 'axis-label', x: padL - 8, y: Y(v) + 4,
        'text-anchor': 'end' }, svg);
      t.textContent = (v > 0 ? '+' : '') + Math.round(v);
    });
    [0, xMid, Math.round(xMax)].forEach(v => {
      const t = el('text', { class: 'axis-label', x: X(v), y: H - 24,
        'text-anchor': 'middle' }, svg);
      t.textContent = Math.round(v);
    });
    const xt = el('text', { class: 'axis-label', x: padL + iw, y: H - 6,
      'text-anchor': 'end' }, svg);
    xt.textContent = opt.xLabel || '';
    const yt = el('text', { class: 'axis-label', x: padL - 8, y: padT - 6,
      'text-anchor': 'end' }, svg);
    yt.textContent = opt.yLabel || '';

    // ラベルが重ならないよう、y順に並べて最小間隔を確保する
    const laid = pts.map(p => ({
      ...p,
      group: p.y > 0 ? (p.x < xMid ? 'rising' : 'core') : 'flat',
      cx: X(p.x), cy: Y(p.y),
      r: 5 + Math.sqrt((p.size || 1) / maxSize) * 8,
    })).sort((a, b) => a.cy - b.cy);
    let prev = -1e9;
    laid.forEach(p => {
      p.ly = Math.max(p.cy, prev + 13);
      prev = p.ly;
    });

    laid.forEach(p => {
      const c = color[p.group];
      const g = el('g', { tabindex: '0' }, svg);
      if (Math.abs(p.ly - p.cy) > 2) {
        el('line', { x1: p.cx + p.r, y1: p.cy, x2: p.cx + p.r + 6, y2: p.ly,
          stroke: grid, 'stroke-width': 1 }, g);
      }
      el('circle', { cx: p.cx, cy: p.cy, r: p.r, fill: c,
        stroke: surface, 'stroke-width': 2 }, g);
      const t = el('text', { x: p.cx + p.r + 8, y: p.ly + 4,
        fill: p.group === 'flat' ? muted : cssVar('--text-primary'),
        'font-size': 12, 'font-weight': p.group === 'rising' ? 700 : 400 }, g);
      t.textContent = p.name;

      const body = `<div class="tt-h">${esc(p.name)}</div>` +
        (p.cat ? `<div class="tt-r">${esc(p.cat)}</div>` : '') +
        `<div class="tt-r">${esc(opt.xLabel || 'x')}<b>${p.x}</b></div>` +
        `<div class="tt-r">${esc(opt.yLabel || 'y')}<b>${p.y > 0 ? '+' : ''}${p.y}</b></div>` +
        `<div class="tt-r">全期間の延べ<b>${p.size}</b></div>`;
      const move = e => showTip(body, e.clientX, e.clientY);
      g.addEventListener('pointermove', move);
      g.addEventListener('pointerenter', move);
      g.addEventListener('pointerleave', hideTip);
    });
  });

  GROUPS.forEach(g => {
    const li = document.createElement('li');
    li.innerHTML = `<span class="swatch" style="background:${cssVar(g.v)}"></span>${esc(g.name)}`;
    legend.appendChild(li);
  });
  const note = document.createElement('li');
  note.style.marginLeft = 'auto';
  note.textContent = '円の大きさ = 全期間の延べ出現数';
  legend.appendChild(note);

  tableView(host, ['技術', 'カテゴリ', opt.xLabel || 'x', opt.yLabel || 'y', '延べ'],
    pts.slice().sort((a, b) => b.y - a.y)
      .map(p => [p.name, p.cat || '', p.x, (p.y > 0 ? '+' : '') + p.y, p.size]));
}
