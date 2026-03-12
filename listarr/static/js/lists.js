// ----------------------
// Lists JavaScript - Dense data table with sort, filter, toggle, run, delete
// ----------------------

// ---------------------
// Constants
// ---------------------

var STORAGE_KEY = 'listarr_running_jobs';
var POLL_INTERVAL_MS = 3000;
var TIMEOUT_MS = 5 * 60 * 1000; // 5 minutes

// Active polling controllers: listId -> intervalId
var activePollers = {};

// ---------------------
// Skeleton management
// ---------------------

/**
 * Hide skeleton rows after initial page load; reveal data rows.
 */
function initSkeleton() {
  requestAnimationFrame(function () {
    var skeletons = document.querySelectorAll('.skeleton-row');
    var dataRows = document.querySelectorAll('.data-row');

    for (var i = 0; i < skeletons.length; i++) {
      skeletons[i].style.display = 'none';
    }
    for (var j = 0; j < dataRows.length; j++) {
      dataRows[j].style.display = '';
    }
  });
}

// ---------------------
// Sort
// ---------------------

var currentSortColumn = 'name';
var currentSortDirection = 'asc';

/**
 * Sort the table by the given column.
 * @param {string} column - data attribute name (e.g. 'name', 'service')
 * @param {string} direction - 'asc' or 'desc'
 */
function sortTable(column, direction) {
  var tbody = document.getElementById('lists-tbody');
  if (!tbody) { return; }

  var rows = [];
  var children = tbody.querySelectorAll('.data-row');
  for (var i = 0; i < children.length; i++) {
    rows.push(children[i]);
  }

  rows.sort(function (a, b) {
    var aVal = (a.getAttribute('data-' + column) || '').toLowerCase();
    var bVal = (b.getAttribute('data-' + column) || '').toLowerCase();
    if (aVal < bVal) { return direction === 'asc' ? -1 : 1; }
    if (aVal > bVal) { return direction === 'asc' ? 1 : -1; }
    return 0;
  });

  for (var j = 0; j < rows.length; j++) {
    tbody.appendChild(rows[j]);
  }

  // Update sort indicators
  var headers = document.querySelectorAll('th[data-sort]');
  for (var k = 0; k < headers.length; k++) {
    var indicator = headers[k].querySelector('.sort-indicator');
    if (!indicator) { continue; }
    if (headers[k].getAttribute('data-sort') === column) {
      indicator.textContent = direction === 'asc' ? '\u2191' : '\u2193';
    } else {
      indicator.textContent = '';
    }
  }
}

/**
 * Initialize sort click handlers on column headers.
 */
function initSort() {
  var headers = document.querySelectorAll('th[data-sort]');
  for (var i = 0; i < headers.length; i++) {
    headers[i].addEventListener('click', function () {
      var col = this.getAttribute('data-sort');
      if (col === currentSortColumn) {
        currentSortDirection = currentSortDirection === 'asc' ? 'desc' : 'asc';
      } else {
        currentSortColumn = col;
        currentSortDirection = 'asc';
      }
      sortTable(currentSortColumn, currentSortDirection);
    });
  }
  // Default sort: name asc
  sortTable('name', 'asc');
}

// ---------------------
// Filter
// ---------------------

/**
 * Filter rows based on service and type dropdowns.
 */
function filterTable() {
  var serviceFilter = document.getElementById('filter-service');
  var typeFilter = document.getElementById('filter-type');
  var serviceVal = serviceFilter ? serviceFilter.value.toLowerCase() : '';
  var typeVal = typeFilter ? typeFilter.value.toLowerCase() : '';

  var rows = document.querySelectorAll('#lists-tbody .data-row');
  for (var i = 0; i < rows.length; i++) {
    var rowService = (rows[i].getAttribute('data-service') || '').toLowerCase();
    var rowType = (rows[i].getAttribute('data-type') || '').toLowerCase();
    var matchService = !serviceVal || rowService === serviceVal;
    var matchType = !typeVal || rowType === typeVal;
    rows[i].style.display = (matchService && matchType) ? '' : 'none';
  }
}

/**
 * Initialize filter dropdown change handlers.
 */
function initFilters() {
  var serviceFilter = document.getElementById('filter-service');
  var typeFilter = document.getElementById('filter-type');
  if (serviceFilter) {
    serviceFilter.addEventListener('change', filterTable);
  }
  if (typeFilter) {
    typeFilter.addEventListener('change', filterTable);
  }
}

// ---------------------
// Status badge helper
// ---------------------

/**
 * Update the status badge in a given row.
 * @param {HTMLElement} row - the <tr> element
 * @param {string} status - 'enabled', 'disabled', 'running', 'error'
 * @param {string} text - display text for the badge
 */
function updateStatusBadge(row, status, text) {
  var badge = row.querySelector('[data-status-badge]');
  if (!badge) { return; }

  var classMap = {
    'enabled': 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success/15 text-success border border-success/30',
    'disabled': 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-bg-hover text-text-muted',
    'running': 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-primary/15 text-primary border border-primary/30',
    'error': 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-error/15 text-error border border-error/30'
  };

  badge.className = classMap[status] || classMap['disabled'];
  badge.textContent = text;
}

// ---------------------
// Toggle switch
// ---------------------

/**
 * Apply visual styling to a toggle switch based on aria-checked state.
 * @param {HTMLButtonElement} btn - the toggle button
 * @param {boolean} isActive - whether the list is active
 */
function applyToggleStyle(btn, isActive) {
  var knob = btn.querySelector('span');
  if (isActive) {
    btn.style.backgroundColor = 'var(--color-success)'; // semantic success token
    btn.style.borderColor = 'transparent'; // no border needed — track fill provides shape
    if (knob) {
      knob.style.transform = 'translateX(16px)'; // translate-x-4
    }
  } else {
    btn.style.backgroundColor = 'var(--color-btn-secondary-bg)'; // semantic inactive state
    btn.style.borderColor = 'var(--color-border)'; // visible border so toggle shape is clear against background
    if (knob) {
      knob.style.transform = 'translateX(0)';
    }
  }
}

/**
 * Initialize toggle switches with initial styling and click handlers.
 */
function initToggleSwitches() {
  var buttons = document.querySelectorAll('button[data-toggle-list]');
  for (var i = 0; i < buttons.length; i++) {
    var btn = buttons[i];
    var isActive = btn.getAttribute('aria-checked') === 'true';
    applyToggleStyle(btn, isActive);

    btn.addEventListener('click', handleToggleClick);
  }
}

/**
 * Handle toggle switch click.
 */
function handleToggleClick() {
  var btn = this;
  var listId = btn.getAttribute('data-toggle-list');
  var row = btn.closest('tr');

  // Loading state
  btn.style.opacity = '0.5';
  btn.disabled = true;

  fetch('/lists/toggle/' + listId, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    }
  })
    .then(function (response) {
      if (!response.ok) {
        throw new Error('HTTP ' + response.status);
      }
      return response.json();
    })
    .then(function (data) {
      if (data.success) {
        var active = data.is_active;
        btn.setAttribute('aria-checked', active ? 'true' : 'false');
        btn.setAttribute('title', active ? 'Disable' : 'Enable');
        applyToggleStyle(btn, active);

        // Update row data attribute
        if (row) {
          row.setAttribute('data-status', active ? 'enabled' : 'disabled');
        }

        // Update status badge
        if (row) {
          updateStatusBadge(row, active ? 'enabled' : 'disabled', active ? 'Enabled' : 'Disabled');
        }

        // Show/hide run button
        if (row) {
          var runBtn = row.querySelector('[data-run-list]');
          if (runBtn) {
            runBtn.style.display = active ? '' : 'none';
          }
        }
      } else {
        if (row) {
          updateStatusBadge(row, 'error', 'Error');
          setTimeout(function () {
            var isNowActive = btn.getAttribute('aria-checked') === 'true';
            updateStatusBadge(row, isNowActive ? 'enabled' : 'disabled', isNowActive ? 'Enabled' : 'Disabled');
          }, 3000);
        }
        showToast(data.message || 'Failed to toggle list status', 'error');
      }
    })
    .catch(function (error) {
      console.error('Error toggling list:', error);
      showToast('Error toggling list. Please try again.', 'error');
    })
    .finally(function () {
      btn.style.opacity = '';
      btn.disabled = false;
    });
}

// ---------------------
// localStorage job tracking
// ---------------------

/**
 * Get running jobs from localStorage.
 * @returns {Object} Map of listId -> {startTime: number}
 */
function getRunningJobs() {
  try {
    var data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : {};
  } catch (e) {
    return {};
  }
}

/**
 * Save running jobs to localStorage.
 * @param {Object} jobs
 */
function saveRunningJobs(jobs) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
  } catch (e) {
    console.error('Error saving running jobs:', e);
  }
}

/**
 * Track a running job.
 * @param {string|number} listId
 * @param {number} startTime
 */
function trackRunningJob(listId, startTime) {
  var jobs = getRunningJobs();
  jobs[listId] = { startTime: startTime };
  saveRunningJobs(jobs);
}

/**
 * Remove a job from tracking.
 * @param {string|number} listId
 */
function removeRunningJob(listId) {
  var jobs = getRunningJobs();
  delete jobs[listId];
  saveRunningJobs(jobs);
}

/**
 * Check if a job is being tracked.
 * @param {string|number} listId
 * @returns {boolean}
 */
function isJobTracked(listId) {
  var jobs = getRunningJobs();
  return !!jobs[String(listId)];
}

// ---------------------
// Run Now
// ---------------------

/**
 * Poll job status until completion or timeout.
 * @param {string|number} listId
 */
function pollJobStatus(listId) {
  if (activePollers[listId]) { return; } // already polling

  var jobs = getRunningJobs();
  if (!jobs[listId]) { return; }

  var startTime = jobs[listId].startTime;

  var intervalId = setInterval(function () {
    var elapsed = Date.now() - startTime;
    if (elapsed > TIMEOUT_MS) {
      clearInterval(activePollers[listId]);
      delete activePollers[listId];
      removeRunningJob(listId);
      var row = document.querySelector('tr[data-list-id="' + listId + '"]');
      if (row) {
        var wasActive = row.getAttribute('data-status') === 'enabled';
        updateStatusBadge(row, wasActive ? 'enabled' : 'disabled', wasActive ? 'Enabled' : 'Disabled');
      }
      showToast('Import is taking longer than expected. Check the activity page.', 'warning');
      return;
    }

    fetch('/lists/' + listId + '/status')
      .then(function (response) {
        if (!response.ok) {
          throw new Error('HTTP ' + response.status);
        }
        return response.json();
      })
      .then(function (data) {
        var row = document.querySelector('tr[data-list-id="' + listId + '"]');
        if (data.status === 'completed') {
          clearInterval(activePollers[listId]);
          delete activePollers[listId];
          removeRunningJob(listId);
          if (row) {
            var isActive = row.getAttribute('data-status') === 'enabled';
            updateStatusBadge(row, isActive ? 'enabled' : 'disabled', isActive ? 'Enabled' : 'Disabled');
          }
        } else if (data.status === 'error' || data.status === 'failed') {
          clearInterval(activePollers[listId]);
          delete activePollers[listId];
          removeRunningJob(listId);
          if (row) {
            updateStatusBadge(row, 'error', 'Error');
            setTimeout(function () {
              var isActive = row.getAttribute('data-status') === 'enabled';
              updateStatusBadge(row, isActive ? 'enabled' : 'disabled', isActive ? 'Enabled' : 'Disabled');
            }, 4000);
          }
        } else if (data.status !== 'running') {
          // Idle or unknown — server restart?
          clearInterval(activePollers[listId]);
          delete activePollers[listId];
          removeRunningJob(listId);
          if (row) {
            var isActive2 = row.getAttribute('data-status') === 'enabled';
            updateStatusBadge(row, isActive2 ? 'enabled' : 'disabled', isActive2 ? 'Enabled' : 'Disabled');
          }
        }
        // status === 'running' → keep polling
      })
      .catch(function (error) {
        console.error('Error polling status for list ' + listId + ':', error);
        // Continue polling on transient errors
      });
  }, POLL_INTERVAL_MS);

  activePollers[listId] = intervalId;
}

/**
 * Restore running states from localStorage on page load.
 */
function restoreRunningStates() {
  var jobs = getRunningJobs();
  for (var listId in jobs) {
    if (!jobs.hasOwnProperty(listId)) { continue; }
    var elapsed = Date.now() - jobs[listId].startTime;
    if (elapsed > TIMEOUT_MS) {
      removeRunningJob(listId);
      continue;
    }
    var row = document.querySelector('tr[data-list-id="' + listId + '"]');
    if (row) {
      updateStatusBadge(row, 'running', 'Running');
    }
    pollJobStatus(listId);
  }
}

/**
 * Initialize Run Now buttons.
 */
function initRunButtons() {
  var buttons = document.querySelectorAll('button[data-run-list]');
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener('click', handleRunClick);
  }
}

/**
 * Handle Run Now button click.
 */
function handleRunClick() {
  var btn = this;
  var listId = btn.getAttribute('data-run-list');
  var row = btn.closest('tr');

  fetch('/lists/' + listId + '/run', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    }
  })
    .then(function (response) {
      return response.json().then(function (data) {
        return { data: data, status: response.status, ok: response.ok };
      });
    })
    .then(function (result) {
      if (result.data.success) {
        // Update badge to Running
        if (row) {
          updateStatusBadge(row, 'running', 'Running');
        }
        var startTime = Date.now();
        trackRunningJob(listId, startTime);
        pollJobStatus(listId);
      } else {
        throw new Error(result.data.message || 'Import failed to start');
      }
    })
    .catch(function (error) {
      console.error('Error running list:', error);
      if (row) {
        updateStatusBadge(row, 'error', 'Error');
        setTimeout(function () {
          var isActive = row.getAttribute('data-status') === 'enabled';
          updateStatusBadge(row, isActive ? 'enabled' : 'disabled', isActive ? 'Enabled' : 'Disabled');
        }, 3000);
      }
    });
}

// ---------------------
// Overflow menu
// ---------------------

/**
 * Close all open overflow menus.
 */
function closeAllOverflowMenus() {
  var menus = document.querySelectorAll('div[data-overflow-menu]');
  for (var i = 0; i < menus.length; i++) {
    menus[i].style.display = 'none';
  }
}

/**
 * Initialize overflow menu toggle logic.
 * Each [...] button toggles its associated dropdown; clicking outside closes all.
 */
function initOverflowMenus() {
  var buttons = document.querySelectorAll('button[data-overflow-list]');
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener('click', function (e) {
      e.stopPropagation();
      var listId = this.getAttribute('data-overflow-list');
      var menu = document.querySelector('div[data-overflow-menu="' + listId + '"]');
      if (!menu) { return; }
      var isOpen = menu.style.display === 'block';
      // Close all menus first (single-open behaviour)
      closeAllOverflowMenus();
      if (!isOpen) {
        // Position fixed dropdown relative to the trigger button
        var rect = this.getBoundingClientRect();
        menu.style.display = 'block';
        var menuW = menu.offsetWidth;
        var menuH = menu.offsetHeight;
        // Horizontal: align right edge to button, clamp to viewport
        var left = rect.right - menuW;
        if (left < 4) { left = 4; }
        if (left + menuW > window.innerWidth - 4) { left = window.innerWidth - menuW - 4; }
        menu.style.left = left + 'px';
        // Vertical: below button, flip up if overflowing
        var top = rect.bottom + 4;
        if (top + menuH > window.innerHeight) {
          top = rect.top - menuH - 4;
        }
        menu.style.top = top + 'px';
      }
    });
  }

  // Close menus on outside click or scroll
  document.addEventListener('click', function () {
    closeAllOverflowMenus();
  });
  window.addEventListener('scroll', closeAllOverflowMenus, true);
}

// ---------------------
// Delete modal
// ---------------------

/**
 * Open the delete modal for a list.
 * @param {string|number} listId
 * @param {string} listName
 */
function openDeleteModal(listId, listName) {
  var modal = document.getElementById('delete-modal');
  var nameSpan = document.getElementById('delete-modal-name');
  var confirmBtn = document.getElementById('delete-modal-confirm');

  if (!modal) { return; }

  if (nameSpan) { nameSpan.textContent = listName; }
  if (confirmBtn) { confirmBtn.setAttribute('data-list-id', listId); }

  modal.style.removeProperty('display');
  modal.style.display = 'flex';
}

/**
 * Close the delete modal.
 */
function closeDeleteModal() {
  var modal = document.getElementById('delete-modal');
  if (modal) {
    modal.style.display = 'none';
  }
}

/**
 * Initialize delete buttons.
 */
function initDeleteButtons() {
  var buttons = document.querySelectorAll('button[data-delete-list]');
  for (var i = 0; i < buttons.length; i++) {
    buttons[i].addEventListener('click', function () {
      var listId = this.getAttribute('data-delete-list');
      var listName = this.getAttribute('data-list-name');
      openDeleteModal(listId, listName);
    });
  }

  // Cancel button
  var cancelBtn = document.getElementById('delete-modal-cancel');
  if (cancelBtn) {
    cancelBtn.addEventListener('click', closeDeleteModal);
  }

  // Backdrop click
  var modal = document.getElementById('delete-modal');
  if (modal) {
    modal.addEventListener('click', function (e) {
      if (e.target === modal) {
        closeDeleteModal();
      }
    });
  }

  // Confirm button
  var confirmBtn = document.getElementById('delete-modal-confirm');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', function () {
      var listId = this.getAttribute('data-list-id');
      if (!listId) { return; }
      handleDeleteConfirm(listId);
    });
  }
}

/**
 * Execute delete request and remove row from DOM.
 * @param {string|number} listId
 */
function handleDeleteConfirm(listId) {
  var confirmBtn = document.getElementById('delete-modal-confirm');
  if (confirmBtn) {
    confirmBtn.disabled = true;
    confirmBtn.textContent = 'Deleting...';
  }

  fetch('/lists/delete/' + listId, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    redirect: 'manual'
  })
    .then(function (response) {
      // Delete endpoint returns a redirect (302) — treat redirected or 2xx as success
      if (response.ok || response.type === 'opaqueredirect' || response.redirected || response.status === 302) {
        return { success: true };
      }
      throw new Error('HTTP ' + response.status);
    })
    .then(function () {
      closeDeleteModal();

      var row = document.querySelector('tr[data-list-id="' + listId + '"]');
      if (row) {
        row.style.transition = 'opacity 0.2s';
        row.style.opacity = '0';
        setTimeout(function () {
          row.remove();
          // Check if any data rows remain
          var remaining = document.querySelectorAll('#lists-tbody .data-row');
          if (remaining.length === 0) {
            // Reload to show empty state
            window.location.reload();
          }
        }, 200);
      }

      if (typeof showToast === 'function') {
        showToast('List deleted successfully', 'success');
      }
    })
    .catch(function (error) {
      console.error('Error deleting list:', error);
      closeDeleteModal();
      if (typeof showToast === 'function') {
        showToast('Error deleting list. Please try again.', 'error');
      }
    })
    .finally(function () {
      if (confirmBtn) {
        confirmBtn.disabled = false;
        confirmBtn.textContent = 'Delete';
      }
    });
}

// ---------------------
// URL success/deleted params
// ---------------------

/**
 * Handle success/deleted query params from server-side redirects.
 */
function handleUrlParams() {
  var urlParams = new URLSearchParams(window.location.search);
  var successAction = urlParams.get('success');
  if (successAction === 'created' || successAction === 'updated') {
    if (typeof showToast === 'function') {
      showToast('List ' + successAction + ' successfully!', 'success');
    }
    var url = new URL(window.location.href);
    url.searchParams.delete('success');
    window.history.replaceState({}, '', url);
  }
  if (urlParams.get('deleted') === 'true') {
    if (typeof showToast === 'function') {
      showToast('List deleted successfully!', 'success');
    }
    var url2 = new URL(window.location.href);
    url2.searchParams.delete('deleted');
    window.history.replaceState({}, '', url2);
  }
}

// ---------------------
// Cleanup
// ---------------------

/**
 * Stop all polling on page unload.
 */
function cleanupPolling() {
  for (var listId in activePollers) {
    if (activePollers.hasOwnProperty(listId)) {
      clearInterval(activePollers[listId]);
    }
  }
}

// ---------------------
// DOMContentLoaded
// ---------------------

document.addEventListener('DOMContentLoaded', function () {
  handleUrlParams();
  initSkeleton();
  initSort();
  initFilters();
  initToggleSwitches();
  initRunButtons();
  initDeleteButtons();
  initOverflowMenus();
  restoreRunningStates();
});

window.addEventListener('beforeunload', cleanupPolling);
