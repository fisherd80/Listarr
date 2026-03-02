// ----------------------
// Activity Detail JavaScript - Run detail page: summary bar, item table, rerun button
// ----------------------

(function () {

  // ---------------------
  // Helpers
  // ---------------------

  function hideLoading() {
    var el = document.getElementById('detail-loading');
    if (el) { el.classList.add('hidden'); }
  }

  function showDetailError(msg) {
    hideLoading();
    var el = document.getElementById('detail-summary');
    if (!el) { return; }
    el.classList.remove('hidden');
    el.textContent = msg;
  }

  function makeEl(tag, className, text) {
    var el = document.createElement(tag);
    if (className) { el.className = className; }
    if (text !== undefined && text !== null) { el.textContent = text; }
    return el;
  }

  // ---------------------
  // Render: Rerun Button
  // ---------------------

  function renderRerunButton(job) {
    if (job.status !== 'failed') { return; }
    var area = document.getElementById('detail-rerun-area');
    if (!area) { return; }

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'inline-flex items-center px-3 py-1.5 text-sm border border-red-600 text-red-400 hover:text-red-300 hover:border-red-500 rounded';
    btn.textContent = 'Rerun';

    btn.addEventListener('click', function () {
      btn.disabled = true;
      btn.textContent = 'Starting...';

      fetch('/api/activity/' + job.id + '/rerun', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        }
      })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          if (data.success) { showToast('Job restarted successfully', 'success'); }
          else { showToast(data.message || 'Failed to restart job', 'error'); }
        })
        .catch(function () { showToast('Failed to restart job', 'error'); })
        .finally(function () { btn.disabled = false; btn.textContent = 'Rerun'; });
    });

    area.appendChild(btn);
  }

  // ---------------------
  // Render: Error Banner
  // ---------------------

  function renderErrorBanner(job) {
    if (job.status !== 'failed' || !job.error_message) { return; }
    var banner = document.getElementById('detail-error-banner');
    if (!banner) { return; }
    banner.textContent = job.error_message;
    banner.classList.remove('hidden');
  }

  // ---------------------
  // Render: Summary Bar
  // ---------------------

  function renderSummary(job) {
    var el = document.getElementById('detail-summary');
    if (!el) { return; }

    var triggerLabel = job.triggered_by === 'scheduled' ? 'Scheduled' : 'Manual';
    var duration = formatDuration(job.duration);
    var timestamp = formatTimestamp(job.started_at, 'absolute');

    // Metadata row
    var metaRow = makeEl('div', 'flex flex-wrap gap-x-4 gap-y-1 mb-2 text-gray-400');
    metaRow.appendChild(makeEl('span', null, job.list_name || 'Unknown list'));
    metaRow.appendChild(makeEl('span', null, '\u2022'));
    metaRow.appendChild(makeEl('span', null, triggerLabel));
    metaRow.appendChild(makeEl('span', null, '\u2022'));
    metaRow.appendChild(makeEl('span', null, timestamp));

    // Counts row
    var countsRow = makeEl('div', 'flex flex-wrap gap-x-3 gap-y-1');
    countsRow.appendChild(makeEl('span', 'text-green-400', 'Added ' + (job.items_added || 0)));
    countsRow.appendChild(makeEl('span', 'text-gray-500', '\u2022'));
    countsRow.appendChild(makeEl('span', null, 'Skipped ' + (job.items_skipped || 0)));
    countsRow.appendChild(makeEl('span', 'text-gray-500', '\u2022'));
    countsRow.appendChild(makeEl('span', 'text-red-400', 'Failed ' + (job.items_failed || 0)));
    countsRow.appendChild(makeEl('span', 'text-gray-500', '\u2022'));
    countsRow.appendChild(makeEl('span', null, 'Duration ' + duration));

    el.appendChild(metaRow);
    el.appendChild(countsRow);
    el.classList.remove('hidden');
  }

  // ---------------------
  // Render: Item Status Badge
  // ---------------------

  function renderItemStatusBadge(status) {
    var colorMap = {
      'added': 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
      'skipped': 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-300',
      'failed': 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
    };
    var colorClass = colorMap[status] || colorMap['skipped'];
    var label = status ? (status.charAt(0).toUpperCase() + status.slice(1)) : 'Unknown';
    return makeEl('span', 'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ' + colorClass, label);
  }

  // ---------------------
  // Render: Reason (with truncation)
  // ---------------------

  function renderReason(message) {
    var MAX_LEN = 60;
    if (!message) { return makeEl('span', null, '-'); }
    if (message.length <= MAX_LEN) { return makeEl('span', null, message); }

    var truncated = message.slice(0, MAX_LEN);
    var wrapper = makeEl('span', 'reason-truncated');
    wrapper.appendChild(document.createTextNode(truncated + '... '));

    var link = document.createElement('a');
    link.href = '#';
    link.className = 'text-primary text-xs reason-expand-link';
    link.textContent = 'more';
    link.setAttribute('data-full', message);
    wrapper.appendChild(link);

    return wrapper;
  }

  // ---------------------
  // Render: Item Table
  // ---------------------

  function renderItemTable(job) {
    var el = document.getElementById('detail-items');
    if (!el) { return; }

    var items = job.items || [];
    var thClass = 'px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider';

    var table = document.createElement('table');
    table.className = 'min-w-full divide-y divide-gray-700';

    // thead
    var thead = document.createElement('thead');
    thead.className = 'border-b border-gray-700';
    var headerRow = document.createElement('tr');
    var cols = ['Title', 'Status', 'Reason', 'TMDB ID'];
    for (var h = 0; h < cols.length; h++) {
      headerRow.appendChild(makeEl('th', thClass, cols[h]));
    }
    thead.appendChild(headerRow);
    table.appendChild(thead);

    // tbody
    var tbody = document.createElement('tbody');
    if (items.length === 0) {
      var emptyRow = document.createElement('tr');
      var emptyCell = document.createElement('td');
      emptyCell.colSpan = 4;
      emptyCell.className = 'px-4 py-8 text-center text-gray-400 text-sm';
      emptyCell.textContent = 'No items recorded for this run.';
      emptyRow.appendChild(emptyCell);
      tbody.appendChild(emptyRow);
    } else {
      for (var i = 0; i < items.length; i++) {
        var item = items[i];
        var row = document.createElement('tr');
        row.className = 'border-b border-gray-700 last:border-0';

        var titleCell = makeEl('td', 'px-4 py-3 text-sm text-gray-100', item.title || 'Unknown');
        var statusCell = makeEl('td', 'px-4 py-3 text-sm');
        statusCell.appendChild(renderItemStatusBadge(item.status));
        var reasonCell = makeEl('td', 'px-4 py-3 text-sm text-gray-400');
        reasonCell.appendChild(renderReason(item.message));
        var tmdbCell = makeEl('td', 'px-4 py-3 text-sm text-gray-500', String(item.tmdb_id || '-'));

        row.appendChild(titleCell);
        row.appendChild(statusCell);
        row.appendChild(reasonCell);
        row.appendChild(tmdbCell);
        tbody.appendChild(row);
      }
    }
    table.appendChild(tbody);
    el.appendChild(table);
    el.classList.remove('hidden');

    el.addEventListener('click', function (event) {
      var target = event.target;
      if (target && target.classList.contains('reason-expand-link')) {
        event.preventDefault();
        var full = target.getAttribute('data-full');
        var parent = target.parentNode;
        if (parent) { parent.textContent = full; }
      }
    });
  }

  // ---------------------
  // Initialization
  // ---------------------

  document.addEventListener('DOMContentLoaded', function () {
    var anchor = document.getElementById('run-id-anchor');
    if (!anchor) {
      showDetailError('Unable to load run detail: missing page anchor.');
      return;
    }

    var runId = anchor.dataset.runId;
    if (!runId || runId === 'undefined') {
      showDetailError('Unable to load run detail: missing run ID.');
      return;
    }

    fetch('/api/activity/' + runId)
      .then(function (response) {
        if (!response.ok) { throw new Error('HTTP ' + response.status); }
        return response.json();
      })
      .then(function (job) {
        hideLoading();
        renderRerunButton(job);
        renderErrorBanner(job);
        renderSummary(job);
        renderItemTable(job);
      })
      .catch(function (err) {
        showDetailError('Failed to load run detail: ' + (err.message || 'Unknown error'));
      });
  });

})();
