function YearRange(selector) {

    console.log(selector)

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

            range: {
                'min': min,
                'max': max
            }
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

function apply_refinements() {

    $('#filter_modal').modal('hide');

    var $refinements = $('#refinements');

    $refinements.empty();

    $(':checked', '#filter_modal').each(function(){
        var $this = $(this);
        var $that = $('<input type="hidden" />');

        $refinements.append($that);
        $that.attr('name', $this.attr('name'));
        $that.val( $this.val() );
    });

    $('form.main-search').submit();

}

function show_refinements() {
    $('#filter_modal').modal('show');
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
    let filterchoices = fg.choices
    for (let i = 0; i < filterchoices.length; i++) {
        const option = document.createElement('option');

        if (selected_options.includes(filterchoices[i].id)) {
            option.selected = true
        }

        option.classList.add('filter-option')
        option.setAttribute('value', filterchoices[i].id)
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
        select.setAttribute('name', filtergroup.id);
        select.setAttribute('multiple', '');
        select.classList.add('form-select');

        buildFilterChoices(filtergroup, select, selected_options);

        searchfield_div.appendChild(select);
    } else {
        search_row.classList.add('search-field-filled');
        const searchfield_div = document.createElement('div');
        searchfield_div.className = 'col filter-group';
        searchfield_div.id = item.textContent;
        const select = document.createElement('select');
        select.setAttribute('name', filtergroup.id);
        select.setAttribute('multiple', '');
        select.classList.add('form-select');

        buildFilterChoices(filtergroup, select, selected_options);

        searchfield_div.appendChild(select);
        item.parentElement.parentElement.insertAdjacentElement('afterend', searchfield_div);
    }
}

function buildYearSlider(item, searchfield_div, selected_years={}) {
    const years = JSON.parse(document.getElementById('years').textContent);

    searchfield_div.id = item.textContent;
    if (item.textContent === 'Start Year') {
        min_year = years.min_start_year;
        max_year = years.max_start_year;
        search_min = selected_years['start-min'] ? selected_years['start-min'] : years.min_start_year;
        search_max = selected_years['start-max'] ? selected_years['start-max'] : years.max_start_year;
    } else {
        min_year = years.min_end_year;
        max_year = years.max_end_year;
        search_min = selected_years['end-min'] ? selected_years['end-min'] : years.min_end_year;
        search_max = selected_years['end-max'] ? selected_years['end-max'] : years.max_end_year;
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

        buildYearSlider(item, searchfield_div, selected_years)
    } else {
        search_row.classList.add('search-field-filled');
        const searchfield_div = document.createElement('div');
        searchfield_div.className = 'col filter-group filter-group-range';

        item.parentElement.parentElement.insertAdjacentElement('afterend', searchfield_div);
        buildYearSlider(item, searchfield_div, selected_years);
    }
}

function populate_table(results) {
    const table = document.getElementById('results-table');
    const table_body = document.getElementById('table-body');
    table_body.remove();
    const new_table = document.createElement('tbody');
    new_table.id = 'table-body';

    for (const result of results) {
        const tr = document.createElement('tr');
        tr.classList.add('hover');
        tr.setAttribute('onclick', `window.location.assign('/db/${result.slug}/')`);
        tr.setAttribute('style', 'cursor: pointer');

        function getThumbnailUrl(path, alias = 'search') {
            // Thumbnail attributes from dbdb/settings.py
            const aliases = {
                search: { width: 200, height: 200 },
                thumb: { width: 280, height: 250 },
                homepage: { width: 100, height: 60 },
                stats: { width: 60, height: 40 },
                recent: { width: 40, height: 40 },
                recommendation: { width: 200, height: 50 },
            };

            if (!path || !aliases[alias]) return `/media/${path}`;

            const { width, height } = aliases[alias];
            return `/media/${path}.${width}x${height}_q85.png`;
        }



        const logo_td = document.createElement('td');
        const logo = document.createElement('img');
        logo.setAttribute('alt', `${result.name}`);
        logo.setAttribute('height', '20px');
        logo.setAttribute('width', 'auto');
        if (result.logo) {
            logo.classList.add(['card-logo', 'card-db-logo']);
            logo.setAttribute('loading', 'lazy');
            if (result.logo.slice(-3) === 'svg') {
                logo.setAttribute('src', `/media/${result.logo}`);
            } else {
                logo.setAttribute('src', `${getThumbnailUrl(result.logo, 'search')}`);
            }
        } else {
            logo.classList.add(['card-logo', 'card-default-logo']);
            logo.setAttribute('src', '/static/core/images/database-nologo.svg');
        }
        logo_td.appendChild(logo);

        const name_td = document.createElement('td');
        name_td.textContent = result.name;

        const start_year_td = document.createElement('td');
        start_year_td.classList.add('text-right');
        if (result.start_year) {
            start_year_td.textContent = result.start_year;
        } else {
            start_year_td.textContent = '—';
        }

        const end_year_td = document.createElement('td');
        end_year_td.classList.add('text-right');
        if (result.end_year) {
            end_year_td.textContent = result.end_year;
        } else {
            end_year_td.textContent = '—';
        }

        tr.appendChild(logo_td);
        tr.appendChild(name_td);
        tr.appendChild(start_year_td);
        tr.appendChild(end_year_td);

        new_table.appendChild(tr);
    }

    table.appendChild(new_table);
}

const collapse = document.getElementById('filter');
const advanced_search_button = document.getElementById('advanced-search-button');

window.addEventListener('DOMContentLoaded', () => {
  if (collapse.classList.contains('show')) {
    collapse.parentElement.classList.add('no-transition', 'bg-active');

    void collapse.offsetWidth;

    collapse.parentElement.classList.remove('no-transition');
  }
});

advanced_search_button.addEventListener('click', () => {
    if (advanced_search_button.classList.contains('collapsed')) {
        collapse.parentElement.classList.remove('bg-active');
    } else {
        collapse.parentElement.classList.add('bg-active');
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const filterdata = JSON.parse(document.getElementById('filterdata').textContent);
    const params = new URLSearchParams(window.location.search);

    const filters = {};
    for (const [key, value] of params.entries()) {
        const filtergroup = filterdata.find(fg => fg.id === key);
        if (filtergroup) {
            if (!filters[key]) {
                filters[key] = []
            }
            filters[key].push(value)
        } else if (key === 'start-min' || key === 'start-max') {
            if (!filters['Start Year']) {
                filters['Start Year'] = {}
            }
            filters['Start Year'][key] = value
        } else if (key === 'end-min' || key === 'end-max') {
            if (!filters['End Year']) {
                filters['End Year'] = {}
            }
            filters['End Year'][key] = value
        } 
    }

    for (const [key, values] of Object.entries(filters)) {
        add_filter_button.call(add_new_button)
        const filtergroup = filterdata.find(fg => fg.id === key);
        if (filtergroup) {
            const item = Array.from(document.getElementById('filter-none').children[0].children[1].children).find(li => li.textContent === filtergroup.label)
            buildFilterGroup(item, values)
        } else {
            const item = Array.from(document.getElementById('filter-none').children[0].children[1].children).find(li => li.textContent === key)
            buildYearFilter(item, values)
        }

        add_new_button = document.getElementById('add_field')
    }

    if (Object.keys(filters).length > 0) {
        const collapse = document.getElementById('filter');
        collapse.classList.add('show');
    }
});

document.addEventListener('click', function(e) {
    if (e.target.matches('.dropdown-item')) {
        item = e.target;
        if (!document.getElementById(item.textContent)) {
            if (item.textContent === 'Start Year' || item.textContent === 'End Year') {
                buildYearFilter(item)
            } else {
                buildFilterGroup(item)
            }
        }
    } else if (e.target.matches('.remove')) {
        item = e.target;
        row = item.parentElement.parentElement;
        row.remove()
    }
});

add_new_button = document.getElementById('add_field');
add_new_button.addEventListener('click', add_filter_button);

document.getElementById('advanced-search-clear').addEventListener('click', function(e) {
    e.preventDefault();
    const url = window.location.origin + window.location.pathname;
    window.location.href = url;
});

// Table sort events
document.getElementById('name-sort').addEventListener('click', function() {
    const results = JSON.parse(document.getElementById('results').textContent);
    const table = document.getElementById('results-table');

    if (table.sort === 'name-asc') {
        results.sort((a, b) => b.name.localeCompare(a.name));
        table.sort = 'name-desc';
    } else {
        results.sort((a, b) => a.name.localeCompare(b.name));
        table.sort = 'name-asc';
    }

    populate_table(results)
});

document.getElementById('start-year-sort').addEventListener('click', function() {
    const results = JSON.parse(document.getElementById('results').textContent);
    const table = document.getElementById('results-table');

    if (table.sort === 'start_year-desc') {
        results.sort((a, b) => {
            if (a.start_year == null && b.start_year == null) return 0;
            if (a.start_year == null) return 1;
            if (b.start_year == null) return -1;

            return a.start_year - b.start_year;
        });
        table.sort = 'start_year-asc';
    } else {
        results.sort((a, b) => {
            if (a.start_year == null && b.start_year == null) return 0;
            if (a.start_year == null) return 1;
            if (b.start_year == null) return -1;

            return b.start_year - a.start_year;
        });
        table.sort = 'start_year-desc';
    }

    populate_table(results)
});

document.getElementById('end-year-sort').addEventListener('click', function() {
    const results = JSON.parse(document.getElementById('results').textContent);
    const table = document.getElementById('results-table');

    if (table.sort === 'end_year-desc') {
        results.sort((a, b) => {
            if (a.end_year == null && b.end_year == null) return 0;
            if (a.end_year == null) return 1;
            if (b.end_year == null) return -1;

            return a.end_year - b.end_year;
        });
        table.sort = 'end_year-asc';
    } else {
        results.sort((a, b) => {
            if (a.end_year == null && b.end_year == null) return 0;
            if (a.end_year == null) return 1;
            if (b.end_year == null) return -1;

            return b.end_year - a.end_year;
        });
        table.sort = 'end_year-desc';
    }

    populate_table(results)
});

$(document).ready(function () {
    var $form = $('form.main-search');

    $('.filters').on('click', 'li.see-more a', function(){
        var $clear = $('a.clear', this);
        var $filtergroup = $(this);
        var $seemore = $('li.see-more', this);

        $clear.click(function(){
            $filtergroup.find(':checked').prop('checked', false);
            $form.submit();
        });

        $seemore.find('a').click(function(){
        var $a = $(this);
        var $ul = $a.closest('ul');
        var $more = $ul.find('.more');

        if ( $a.hasClass('active') ) {
            $more.hide();
            $a.text('Show more');
            $a.removeClass('active');
        }
        else {
            $more.show();
            $a.text('Show less');
            $a.addClass('active');
        }
        });
    });

    $('.filter-group :checkbox').change(function(){
        $form.submit();
    });

    $('#filter_modal').modal({
        show: false
    });

});

// Browse Page Search Box
$("#mainsearch").find('input[name="q"]').autoComplete({
    minChars: 3,
    source: function(term, response) {
        $.getJSON('/search/autocomplete/', { q: term }, function(data) { response(data); });
    }
});

