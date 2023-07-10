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

$(document).ready(function () {

    new YearRange('#start_year');
    new YearRange('#end_year');

    var $form = $('form.main-search');

    $('.filter-group').each(function(){
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
