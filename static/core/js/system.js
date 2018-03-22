(function ($){
	var $token = $('meta').filter('[name="counter"]');
	
	if ( $token.length == 1 ) {
		var token = $token.attr('content');
		jQuery.post('/counter', { token:token });
	}

	$('.markdown-area').each(function () {
		var text = $.trim($(this).text());
		var md = markdown.toHTML(text);
		$(this).html(md);
	});

	$('div.has-citations').each(function(){
		var $this = $(this);
		var $info = $this.find('a.citations');
		var $cite = $this.find('cite');

		if ( $cite.find('li').length > 0 ) {
			$info.popover({
				container: 'body',
				content: $cite.html(),
				html: true,
				title: 'Citations'
			});
			
			$info.on('show.bs.popover', function() {
				$('a.citations.active').popover('hide');
			});
			$info.on('shown.bs.popover', function() {
				$info.addClass('active');
			});
			$info.on('hidden.bs.popover', function() {
				$info.removeClass('active');
			});
		}
		else {
			$info.addClass('hidden').hide();
		}
	});
}(jQuery));
