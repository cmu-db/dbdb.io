
$(document).ready(function() {
  $(".revision-button").click(function() {
    window.location.href = $(this).attr("data-url");
  });

  $('.description').each(function () {
    $(this).html(markdown.toHTML($(this).text().trim()))
  })

});
