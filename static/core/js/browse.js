function YearRange(selector) {
    var self = this;
    var $elem = $(selector);
    var $btn_toggle = $elem.find('button.btn-toggle');
    var $input_min = $elem.find('input[for="min"]');
    var $input_max = $elem.find('input[for="max"]');
    var $var_min = $elem.find('var[for="min"]');
    var $var_max = $elem.find('var[for="max"]');
    var $range = $elem.find('div.range');
    var range = $range[0];

    var initial_state = null;
    var min = parseInt( $elem.data('min') , 10 );
    var max = parseInt( $elem.data('max') , 10 );
    var selected_min = $input_min.val() ? parseInt( $input_min.val() , 10 ) : '';
    var selected_max = $input_max.val() ? parseInt( $input_max.val() , 10 ) : '';

    self.update = function update(values, handle) {
        if ( ! $elem.hasClass('active') ) return;

        var val = parseInt( values[handle] , 10 );

        if ( handle == 0 ) {
            $input_min.val(val);
            $var_min.text(val);
            if (val != selected_min) $elem.addClass('changed');
        }
        else if ( handle == 1 ) {
            $input_max.val(val);
            $var_max.text(val);
            if (val != selected_max) $elem.addClass('changed');
        }
    };

    self.toggle = function toggle() {
        if ( $elem.hasClass('active') ) {
            self.disable();
        }
        else {
            self.enable();
        }
        $elem.addClass('changed');
    };

    self.enable = function enable() {
        $elem.addClass('active');
        $range.show();
        $btn_toggle.text('Enabled');
        $input_min.prop('disabled', false);
        $input_max.prop('disabled', false);
        var values = range.noUiSlider.get();
        self.update(values, 0);
        self.update(values, 1);
    };

    self.disable = function disable() {
        $elem.removeClass('active');
        $range.hide();
        $btn_toggle.text('Enable');
        $input_min.prop('disabled', true);
        $input_max.prop('disabled', true);
        $input_min.val('');
        $input_max.val('');
    };

    self.init = function init() {
        if ( selected_min && selected_max ) {
            $elem.addClass('active');
        }

        noUiSlider.create(range, {
            connect: true,
            start: [selected_min ? selected_min : min, selected_max ? selected_max : max],
            step: 1,
            range: { 'min': min, 'max': max }
        });

        range.noUiSlider.on('update', self.update);

        if ( $elem.hasClass('active') ) {
            initial_state = 'active';
            self.enable();
        }
        else {
            initial_state = 'disabled';
            self.disable();
        }

        $btn_toggle.click(self.toggle);
    };
    self.init();
}

function add_filter_button() {
    const template = document.getElementById('template');
    const copy = template.cloneNode(true);
    copy.hidden = false;
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
    item.parentElement.previousElementSibling.textContent = item.textContent;

    const filterdata = JSON.parse(document.getElementById('filterdata').textContent);
    const filtergroup = filterdata.find(fg => fg.label === item.textContent);

    item.parentElement.parentElement.parentElement.id = 'filter-' + filtergroup.id;

    const search_row = item.parentElement.parentElement.parentElement;
    if (search_row.classList.contains('search-field-filled')) {
        const searchfield_div = item.parentElement.parentElement.nextElementSibling;
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
        search_row.classList.add('search-field-filled');
        const searchfield_div = document.createElement('div');
        searchfield_div.className = 'col filter-group';
        searchfield_div.id = item.textContent;
        const select = document.createElement('select');
        select.id = filtergroup.id + '-choices';
        select.setAttribute('name', filtergroup.id);
        select.setAttribute('multiple', '');
        select.classList.add('choices-multiple');

        buildFilterChoices(filtergroup, select, selected_options);

        searchfield_div.appendChild(select);
        item.parentElement.parentElement.insertAdjacentElement('afterend', searchfield_div);
        new Choices(select, {
            removeItemButton: true,
            removeItems: true,
            shouldSort: false,
            duplicateItemsAllowed: false,
            maxItemCount: -1,
        });
    }
}

function buildYearSlider(item, searchfield_div, selected_years={}) {
    const years = JSON.parse(document.getElementById('years').textContent);

    searchfield_div.id = item.textContent;
    if (item.textContent === 'Start Year') {
        min_year = years.min_start_year;
        max_year = years.max_start_year;
        search_min = /^\d+$/.test(selected_years['start-min']) ? selected_years['start-min'] : years.min_start_year;
        search_max = /^\d+$/.test(selected_years['start-max']) ? selected_years['start-max'] : years.max_start_year;
    } else {
        min_year = years.min_end_year;
        max_year = years.max_end_year;
        search_min = /^\d+$/.test(selected_years['end-min']) ? selected_years['end-min'] : years.min_end_year;
        search_max = /^\d+$/.test(selected_years['end-max']) ? selected_years['end-max'] : years.max_end_year;
    }

    searchfield_div.setAttribute('data-min', min_year);
    searchfield_div.setAttribute('data-max', max_year);

    const h3 = document.createElement('h3');
    const span = document.createElement('span');
    span.className = 'years';
    const min = document.createElement('var');
    min.setAttribute('for', 'min');
    const max = document.createElement('var');
    max.setAttribute('for', 'max');
    span.append('(', min, ' - ', max, ')');
    h3.appendChild(span);

    const range_container_div = document.createElement('div');
    range_container_div.className = 'range-container';
    const range_div = document.createElement('div');
    range_div.className = 'range';
    range_container_div.appendChild(range_div);

    const input_min = document.createElement('input');
    input_min.setAttribute('type', 'hidden');
    input_min.setAttribute('name', `${item.textContent.split(' ')[0].toLowerCase()}-min`);
    input_min.setAttribute('for', 'min');
    input_min.setAttribute('value', search_min);

    const input_max = document.createElement('input');
    input_max.setAttribute('type', 'hidden');
    input_max.setAttribute('name', `${item.textContent.split(' ')[0].toLowerCase()}-max`);
    input_max.setAttribute('for', 'max');
    input_max.setAttribute('value', search_max);

    searchfield_div.appendChild(h3);
    searchfield_div.appendChild(range_container_div);
    searchfield_div.appendChild(input_min);
    searchfield_div.appendChild(input_max);

    new YearRange(`#${item.textContent.replace(/ /g, '\\ ')}`);
}

function buildYearFilter(item, selected_years) {
    item.parentElement.previousElementSibling.textContent = item.textContent;
    item.parentElement.parentElement.parentElement.id = 'filter-' + item.textContent;

    const search_row = item.parentElement.parentElement.parentElement;
    if (search_row.classList.contains('search-field-filled')) {
        const searchfield_div = item.parentElement.parentElement.nextElementSibling;
        searchfield_div.innerHTML = '';
        buildYearSlider(item, searchfield_div, selected_years);
    } else {
        search_row.classList.add('search-field-filled');
        const searchfield_div = document.createElement('div');
        searchfield_div.className = 'col filter-group filter-group-range';
        item.parentElement.parentElement.insertAdjacentElement('afterend', searchfield_div);
        buildYearSlider(item, searchfield_div, selected_years);
    }
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
    } else if (e.target.matches('.remove')) {
        const row = e.target.parentElement.parentElement;
        row.remove();
    }
});

add_new_button = document.getElementById('add_field');
add_new_button.addEventListener('click', add_filter_button);

document.getElementById('advanced-search-clear').addEventListener('click', function(e) {
    e.preventDefault();
    document.querySelectorAll('.filter-group').forEach(el => {
        if (el.id !== 'template') el.remove();
    });
});

// ── Table sort ───────────────────────────────────────────────────────────────

const sortState = { column: 'name', order: 'asc' };

const arrowIds = {
    name:      { asc: 'name-asc-arrow',  desc: 'name-dec-arrow'  },
    startYear: { asc: 'start-asc-arrow', desc: 'start-dec-arrow' },
    endYear:   { asc: 'end-asc-arrow',   desc: 'end-dec-arrow'   },
};

function updateSortArrows(column, order) {
    document.querySelectorAll('.sort-arrow').forEach(el => { el.style.opacity = '0.2'; });
    const id = arrowIds[column][order === 'asc' ? 'asc' : 'desc'];
    document.getElementById(id).style.opacity = '1';
}

function sortTableBy(column, order) {
    const tbody = document.getElementById('table-body');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr.browse-row'));

    rows.sort((a, b) => {
        if (column === 'name') {
            const aVal = a.dataset.name || '';
            const bVal = b.dataset.name || '';
            return order === 'asc' ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
        }
        const aRaw = a.dataset[column];
        const bRaw = b.dataset[column];
        const aVal = aRaw ? parseInt(aRaw) : null;
        const bVal = bRaw ? parseInt(bRaw) : null;
        if (aVal === null && bVal === null) return 0;
        if (aVal === null) return 1;
        if (bVal === null) return -1;
        return order === 'asc' ? aVal - bVal : bVal - aVal;
    });

    rows.forEach(row => tbody.appendChild(row));
}

function handleSortClick(column) {
    const newOrder = (sortState.column === column && sortState.order === 'asc') ? 'desc' : 'asc';
    sortState.column = column;
    sortState.order = newOrder;
    updateSortArrows(column, newOrder);
    sortTableBy(column, newOrder);
}

const nameSortBtn = document.getElementById('name-sort');
const startSortBtn = document.getElementById('start-year-sort');
const endSortBtn = document.getElementById('end-year-sort');

if (nameSortBtn)  nameSortBtn.addEventListener('click',  () => handleSortClick('name'));
if (startSortBtn) startSortBtn.addEventListener('click', () => handleSortClick('startYear'));
if (endSortBtn)   endSortBtn.addEventListener('click',   () => handleSortClick('endYear'));

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
        $.getJSON('/search/autocomplete/', { q: term }, function(data) { response(data); });
    },
    onSelect: function(e, term, item) { window.location.href = "/db/" + convertToSlug(term); }
});
