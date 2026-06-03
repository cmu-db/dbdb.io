function add_filter_button() {
    const template = document.getElementById('template');
    const copy = template.cloneNode(true);
    copy.classList.remove('d-none');
    copy.classList.add('d-flex');
    copy.id = 'filter-none';
    const button_container = document.getElementById('advanced-search-btn-container');
    button_container.insertAdjacentElement('beforebegin', copy);
}

function buildFilterChoices(fg, select, selected_options) {
    let filterchoices = fg.choices;
    for (let i = 0; i < filterchoices.length; i++) {
        const option = document.createElement('option');
        if (selected_options.includes(filterchoices[i].id)) {
            option.selected = true;
        }
        option.classList.add('filter-option');
        option.setAttribute('value', filterchoices[i].id);
        option.textContent = filterchoices[i].label;
        select.appendChild(option);
    }
}

function buildFilterGroup(item, selected_options=[]) {
    item.parentElement.previousElementSibling.innerHTML =
        item.textContent + ' <i class="fas fa-chevron-down chev"></i>';

    const filterdata = JSON.parse(document.getElementById('filterdata').textContent);
    const filtergroup = filterdata.find(fg => fg.label === item.textContent);

    const dropdownDiv = item.parentElement.parentElement;
    const filterRow   = dropdownDiv.parentElement;
    filterRow.id      = 'filter-' + filtergroup.id;

    const existingYear = filterRow.querySelector('.year-control');
    if (existingYear) existingYear.remove();

    if (filterRow.classList.contains('search-field-filled')) {
        const searchfield_div = filterRow.querySelector('.filter-control');
        searchfield_div.innerHTML = '';
        searchfield_div.id = item.textContent;
        const select = document.createElement('select');
        select.id = filtergroup.id + '-choices';
        select.setAttribute('name', filtergroup.id);
        select.setAttribute('multiple', '');
        select.classList.add('form-select');

        buildFilterChoices(filtergroup, select, selected_options);

        searchfield_div.appendChild(select);
        new Choices(select, {
            removeItemButton: true,
            removeItems: true,
            shouldSort: false,
            duplicateItemsAllowed: false,
            maxItemCount: -1,
        });
    } else {
        filterRow.classList.add('search-field-filled');
        const searchfield_div = document.createElement('div');
        searchfield_div.className = 'filter-control';
        searchfield_div.id = item.textContent;
        const select = document.createElement('select');
        select.id = filtergroup.id + '-choices';
        select.setAttribute('name', filtergroup.id);
        select.setAttribute('multiple', '');
        select.classList.add('choices-multiple');

        buildFilterChoices(filtergroup, select, selected_options);

        searchfield_div.appendChild(select);
        filterRow.querySelector('.row-remove-desktop').insertAdjacentElement('beforebegin', searchfield_div);
        new Choices(select, {
            removeItemButton: true,
            removeItems: true,
            shouldSort: false,
            duplicateItemsAllowed: false,
            maxItemCount: -1,
        });
    }
}

function buildYearSlider(item, yearControl, selected_years = {}) {
    const years = JSON.parse(document.getElementById('years').textContent);
    const isStart = item.textContent === 'Start Year';

    const min_year   = isStart ? years.min_start_year : years.min_end_year;
    const max_year   = isStart ? years.max_start_year : years.max_end_year;
    const search_min = isStart
        ? (/^\d+$/.test(selected_years['start-min']) ? +selected_years['start-min'] : min_year)
        : (/^\d+$/.test(selected_years['end-min'])   ? +selected_years['end-min']   : min_year);
    const search_max = isStart
        ? (/^\d+$/.test(selected_years['start-max']) ? +selected_years['start-max'] : max_year)
        : (/^\d+$/.test(selected_years['end-max'])   ? +selected_years['end-max']   : max_year);

    const namePrefix = isStart ? 'start' : 'end';
    const capText    = isStart ? 'Founded between' : 'Discontinued between';

    yearControl.id = item.textContent;

    const head = document.createElement('div');
    head.className = 'year-head';

    const cap = document.createElement('span');
    cap.className = 'yr-cap';
    cap.textContent = capText;

    const readout = document.createElement('span');
    readout.className = 'yr-range';
    readout.innerHTML = search_min + ' <span class="sep">–</span> ' + search_max;

    head.append(cap, readout);

    const sliderEl = document.createElement('div');
    sliderEl.className = 'year-slider';

    const bounds = document.createElement('div');
    bounds.className = 'year-bounds';
    bounds.innerHTML = '<span>' + min_year + '</span><span>' + max_year + '</span>';

    const inputMin = document.createElement('input');
    inputMin.type = 'hidden';
    inputMin.name = namePrefix + '-min';
    inputMin.value = search_min;

    const inputMax = document.createElement('input');
    inputMax.type = 'hidden';
    inputMax.name = namePrefix + '-max';
    inputMax.value = search_max;

    yearControl.innerHTML = '';
    yearControl.append(head, sliderEl, bounds, inputMin, inputMax);

    noUiSlider.create(sliderEl, {
        start: [search_min, search_max],
        connect: true,
        step: 1,
        margin: 1,
        range: { min: min_year, max: max_year },
        format: {
            to: function (v) { return Math.round(v); },
            from: function (v) { return Number(v); }
        }
    });

    sliderEl.noUiSlider.on('update', function (values) {
        readout.innerHTML = values[0] + ' <span class="sep">–</span> ' + values[1];
        inputMin.value = values[0];
        inputMax.value = values[1];
    });
}

function buildYearFilter(item, selected_years) {
    // item → li.dropdown-item
    // item.parentElement → ul.dropdown-menu
    // item.parentElement.previousElementSibling → button.field-pick
    // item.parentElement.parentElement → div.dropdown
    // item.parentElement.parentElement.parentElement → div.filter-row

    item.parentElement.previousElementSibling.innerHTML =
        item.textContent + ' <i class="fas fa-chevron-down chev"></i>';

    const dropdownDiv = item.parentElement.parentElement;
    const filterRow   = dropdownDiv.parentElement;
    filterRow.id      = 'filter-' + item.textContent;

    const existingControl = filterRow.querySelector('.filter-control');
    if (existingControl) {
        existingControl.remove();
        filterRow.classList.remove('search-field-filled');
    }

    let yearControl = filterRow.querySelector('.year-control');
    if (!yearControl) {
        yearControl = document.createElement('div');
        yearControl.className = 'year-control';
        filterRow.querySelector('.row-remove-desktop').insertAdjacentElement('beforebegin', yearControl);
    }
    buildYearSlider(item, yearControl, selected_years);
}

// ── Collapsible panels (Advanced Search + Columns) ───────────────────────────

function initCollapsiblePanel(panelId, buttonId, arrowId) {
    const panel  = document.getElementById(panelId);
    const button = document.getElementById(buttonId);
    const arrow  = document.getElementById(arrowId);
    if (!panel || !button || !arrow) return;

    // Sync bg-active / open classes on page load without animation
    window.addEventListener('DOMContentLoaded', () => {
        if (panel.classList.contains('show')) {
            panel.parentElement.classList.add('no-transition', 'bg-active');
            arrow.classList.add('no-transition', 'open');
            void panel.offsetWidth; // force reflow to flush no-transition
            panel.parentElement.classList.remove('no-transition');
            arrow.classList.remove('no-transition');
        }
    });

    // Keep bg-active / open in sync as Bootstrap toggles the panel
    button.addEventListener('click', () => {
        if (button.classList.contains('collapsed')) {
            panel.parentElement.classList.remove('bg-active');
            arrow.classList.remove('open');
        } else {
            panel.parentElement.classList.add('bg-active');
            arrow.classList.add('open');
        }
    });
}

initCollapsiblePanel('filter',        'advanced-search-button', 'advanced-arrow');
initCollapsiblePanel('columns-panel', 'columns-button',         'columns-arrow');

const applyColsBtn = document.getElementById('apply-columns');
if (applyColsBtn) {
    applyColsBtn.addEventListener('click', function () {
        const checked = Array.from(document.querySelectorAll('.col-checkbox:checked')).map(cb => cb.value);
        const params = new URLSearchParams(window.location.search);
        params.delete('cols');
        if (checked.length > 0) {
            params.set('cols', checked.join(','));
        }
        window.location.search = params.toString();
    });
}

// Preserve col selection when the search form is submitted
const mainSearchForm = document.getElementById('mainsearch');
if (mainSearchForm) {
    mainSearchForm.addEventListener('submit', function () {
        const checked = Array.from(document.querySelectorAll('.col-checkbox:checked')).map(cb => cb.value);
        let input = this.querySelector('input[name="cols"]');
        if (checked.length > 0) {
            if (!input) {
                input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'cols';
                this.appendChild(input);
            }
            input.value = checked.join(',');
        } else if (input) {
            input.remove();
        }
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const filterdata = JSON.parse(document.getElementById('filterdata').textContent);
    const params = new URLSearchParams(window.location.search);

    const filters = {};
    for (const [key, value] of params.entries()) {
        const filtergroup = filterdata.find(fg => fg.id === key);
        if (filtergroup) {
            if (!filters[key]) filters[key] = [];
            filters[key].push(value);
        } else if (key === 'start-min' || key === 'start-max') {
            if (!filters['Start Year']) filters['Start Year'] = {};
            filters['Start Year'][key] = value;
        } else if (key === 'end-min' || key === 'end-max') {
            if (!filters['End Year']) filters['End Year'] = {};
            filters['End Year'][key] = value;
        }
    }

    for (const [key, values] of Object.entries(filters)) {
        add_filter_button.call(add_new_button);
        const filtergroup = filterdata.find(fg => fg.id === key);
        if (filtergroup) {
            const item = Array.from(document.getElementById('filter-none').children[0].children[1].children).find(li => li.textContent === filtergroup.label);
            buildFilterGroup(item, values);
        } else {
            const item = Array.from(document.getElementById('filter-none').children[0].children[1].children).find(li => li.textContent === key);
            buildYearFilter(item, values);
        }
        add_new_button = document.getElementById('add_field');
    }

    if (Object.keys(filters).length > 0) {
        const collapse = document.getElementById('filter');
        collapse.classList.add('show');
        const first_field = document.getElementById('filter-none');
        first_field.remove();
    }
});

document.addEventListener('click', function(e) {
    if (e.target.matches('.dropdown-item')) {
        const item = e.target;
        if (!document.getElementById(item.textContent)) {
            if (item.textContent === 'Start Year' || item.textContent === 'End Year') {
                buildYearFilter(item);
            } else {
                buildFilterGroup(item);
            }
        }
    } else if (e.target.closest('.row-remove')) {
        e.target.closest('.filter-row').remove();
    }
});

add_new_button = document.getElementById('add_field');
add_new_button.addEventListener('click', add_filter_button);

document.getElementById('advanced-search-clear').addEventListener('click', function(e) {
    e.preventDefault();
    document.querySelectorAll('.filter-row').forEach(el => {
        if (el.id !== 'template') el.remove();
    });
});

// ── Table sort ───────────────────────────────────────────────────────────────

const sortState = { btn: null, order: 'asc' };

function updateSortArrows(activeBtn, order) {
    document.querySelectorAll('.sort-btn .sort-arrow').forEach(el => { el.style.opacity = '0.2'; });
    if (!activeBtn) return;
    const arrows = activeBtn.querySelectorAll('.sort-arrow');
    if (order === 'asc'  && arrows[0]) arrows[0].style.opacity = '1';
    if (order === 'desc' && arrows[1]) arrows[1].style.opacity = '1';
}

function sortTableBy(btn, order) {
    const tbody = document.getElementById('table-body');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr.browse-row'));
    const colIndex = parseInt(btn.dataset.sortCol);
    const sortType = btn.dataset.sortType || 'text';

    rows.sort((a, b) => {
        const aRaw = a.cells[colIndex] ? (a.cells[colIndex].dataset.sortVal || '') : '';
        const bRaw = b.cells[colIndex] ? (b.cells[colIndex].dataset.sortVal || '') : '';
        if (sortType === 'numeric') {
            const aVal = aRaw !== '' ? parseInt(aRaw) : null;
            const bVal = bRaw !== '' ? parseInt(bRaw) : null;
            if (aVal === null && bVal === null) return 0;
            if (aVal === null) return 1;
            if (bVal === null) return -1;
            return order === 'asc' ? aVal - bVal : bVal - aVal;
        }
        return order === 'asc' ? aRaw.localeCompare(bRaw) : bRaw.localeCompare(aRaw);
    });

    rows.forEach(row => tbody.appendChild(row));
}

function handleSortClick(btn) {
    const newOrder = (sortState.btn === btn && sortState.order === 'asc') ? 'desc' : 'asc';
    sortState.btn = btn;
    sortState.order = newOrder;
    updateSortArrows(btn, newOrder);
    sortTableBy(btn, newOrder);
}

document.querySelectorAll('.sort-btn').forEach(btn => {
    btn.addEventListener('click', () => handleSortClick(btn));
});

// Initialise sort from ?order-by= param, falling back to name column ascending
(function () {
    const param = new URLSearchParams(window.location.search).get('order-by') || '';
    const desc = param.startsWith('-');
    const colId = param.replace(/^[+-]/, '') || 'name';
    const order = desc ? 'desc' : 'asc';
    const btn = document.querySelector(`.sort-btn[data-col-id="${colId}"]`)
             || document.querySelector('.sort-btn[data-sort-col="1"]');
    if (btn) {
        sortState.btn = btn;
        sortState.order = order;
        updateSortArrows(btn, order);
        sortTableBy(btn, order);
    }
}());

// ── Row click navigation ─────────────────────────────────────────────────────

const tableBody = document.getElementById('table-body');
if (tableBody) {
    tableBody.addEventListener('click', function(e) {
        if (e.target.closest('a')) return;
        const row = e.target.closest('tr.browse-row');
        if (!row || !row.dataset.href) return;
        if (e.ctrlKey || e.metaKey || e.shiftKey) {
            window.open(row.dataset.href, '_blank');
        } else {
            window.location.href = row.dataset.href;
        }
    });
}

// ── Browse page search autocomplete ─────────────────────────────────────────

$("#mainsearch").find('input[name="q"]').autoComplete({
    minChars: 3,
    source: function(term, response) {
        $.getJSON('/api/systems/autocomplete/', { q: term }, function(data) { response(data); });
    },
    onSelect: function(e, term, item) { window.location.href = "/db/" + convertToSlug(term); }
});
