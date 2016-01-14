
$(document).ready(function() {
  $(".revision-button").click(function() {
    window.location.href = $(this).attr("data-url");
  });
})