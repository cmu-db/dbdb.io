

$(document).ready(function() {
  $(".ranking-row").click(function() {
    window.location.href = $(this).attr("data-url");
  })
})