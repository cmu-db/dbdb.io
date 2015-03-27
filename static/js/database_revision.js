
$(document).ready(function() {
  $(".revision-row").click(function() {
    window.location.href = $(this).attr("data-url");
  })
})