const $ = id => document.getElementById(id);
let history = [], timer = null, loading = false;
const names = {median_baseline: 'Median baseline', ridge: 'Ridge regression', random_forest: 'Random forest'};

async function get(url) {
  const response = await fetch(url);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || 'Could not load data');
  return body;
}
function showError(error) {
  $('error').textContent = error.message;
  $('error').hidden = false;
  stop();
}
function stop() {
  clearInterval(timer);
  timer = null;
  $('play').textContent = 'Play history';
}
function chart(container, rows, series, label, threshold = null) {
  const width = 960, height = 260, left = 57, right = 25, top = 22, bottom = 35;
  const values = rows.flatMap(row => series.map(item => row[item.key]));
  if (threshold !== null) values.push(threshold);
  let low = threshold !== null ? 0 : Math.min(...values);
  let high = Math.max(...values);
  const padding = Math.max((high - low) * .12, 1);
  high += padding;
  if (threshold === null) low -= padding;
  const maxCycle = Math.max(rows.at(-1).cycle, 2);
  const x = cycle => left + (cycle - 1) / (maxCycle - 1) * (width - left - right);
  const y = value => height - bottom - (value - low) / (high - low) * (height - top - bottom);
  let svg = `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="${label}">`;
  for (let i = 0; i <= 4; i++) {
    const value = low + (high - low) * i / 4;
    svg += `<line x1="${left}" x2="${width-right}" y1="${y(value)}" y2="${y(value)}" stroke="#e9eeeb"/><text x="${left-10}" y="${y(value)+4}" text-anchor="end" fill="#7b898b" font-size="11">${value.toFixed(high > 100 ? 0 : 1)}</text>`;
  }
  if (threshold !== null) svg += `<line x1="${left}" x2="${width-right}" y1="${y(threshold)}" y2="${y(threshold)}" stroke="#bc7d31" stroke-dasharray="5 5"/>`;
  for (const item of series) {
    const points = rows.map(row => `${x(row.cycle)},${y(row[item.key])}`).join(' ');
    svg += `<polyline points="${points}" fill="none" stroke="${item.color}" stroke-width="2.5" stroke-linejoin="round"/>`;
    const last = rows.at(-1);
    svg += `<circle cx="${x(last.cycle)}" cy="${y(last[item.key])}" r="3.5" fill="${item.color}"/>`;
  }
  svg += `<text x="${left}" y="${height-9}" fill="#7b898b" font-size="11">Cycle 1</text><text x="${width-right}" y="${height-9}" text-anchor="end" fill="#7b898b" font-size="11">Cycle ${rows.at(-1).cycle}</text></svg>`;
  $(container).innerHTML = svg;
}
function render() {
  if (!history.length) return;
  const position = Number($('cycle').value);
  const rows = history.slice(0, position), current = rows.at(-1);
  $('cycleLabel').textContent = `${current.cycle} / ${history.length}`;
  $('remaining').textContent = current.predicted_rul.toFixed(1);
  $('status').textContent = current.warning ? 'Check engine' : 'No warning';
  $('status').className = `number status ${current.warning ? 'warn' : ''}`;
  const series = [{key: 'predicted_rul', color: '#167d74'}];
  if ($('truth').checked) series.push({key: 'actual_rul', color: '#9aa6ab'});
  chart('lifeChart', rows, series, 'Remaining operating cycles over time', 30);
  chart('sensorChart', rows, [{key: $('sensor').value, color: '#627d99'}], 'Selected sensor readings over time');
}
async function loadMachine() {
  stop(); loading = true;
  for (const id of ['engine', 'play', 'reset', 'cycle']) $(id).disabled = true;
  try {
    const data = await get(`/api/machines/${encodeURIComponent($('engine').value)}`);
    history = data.history;
    if (!history.length) throw new Error('No predictions are available for this engine.');
    $('cycle').max = history.length;
    $('cycle').value = Math.min(10, history.length);
    $('error').hidden = true;
    render();
  } catch (error) { showError(error); }
  finally {
    loading = false;
    for (const id of ['engine', 'play', 'reset', 'cycle']) $(id).disabled = false;
  }
}
$('engine').addEventListener('change', loadMachine);
$('cycle').addEventListener('input', () => {stop(); render();});
$('truth').addEventListener('change', render);
$('sensor').addEventListener('change', render);
$('reset').addEventListener('click', () => {stop(); $('cycle').value = 1; render();});
$('play').addEventListener('click', () => {
  if (loading) return;
  if (timer) {stop(); return;}
  if (Number($('cycle').value) >= history.length) $('cycle').value = 1;
  $('play').textContent = 'Pause';
  timer = setInterval(() => {
    $('cycle').value = Number($('cycle').value) + 1;
    render();
    if (Number($('cycle').value) >= history.length) stop();
  }, 180);
});
async function start() {
  try {
    const [summary, machines] = await Promise.all([get('/api/summary'), get('/api/machines')]);
    $('mae').textContent = summary.test[summary.selected_model].mae.toFixed(1);
    $('model').textContent = names[summary.selected_model];
    $('comparison').replaceChildren();
    for (const [model, validation] of Object.entries(summary.validation)) {
      const row = document.createElement('tr'), result = summary.test[model];
      const values = [names[model] + (model === summary.selected_model ? ' · selected' : ''), validation.mae.toFixed(1), result.mae.toFixed(1), `${(100*result.warning_precision).toFixed(1)}%`, `${(100*result.warning_recall).toFixed(1)}%`];
      for (const value of values) { const cell = document.createElement('td'); cell.textContent = value; row.append(cell); }
      if (model === summary.selected_model) row.className = 'selected';
      $('comparison').append(row);
    }
    $('engine').replaceChildren(...machines.map(machine => new Option(machine.machine_id, machine.machine_id)));
    if (!machines.length) throw new Error('No held-out engines found. Run prepare first.');
    await loadMachine();
  } catch (error) {showError(error);}
}
start();
