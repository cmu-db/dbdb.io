

$(document).ready(function() {
  $(".ranking-row").click(function() {
    window.location.href = $(this).attr("data-url");
  });

  $(".as-button").click(function() {
    if ($(this).hasClass("active")) {
      $(".as-on").hide(500);
      $(".as-off").show(500);
    } else {
      $(".as-off").hide(500);
      $(".as-on").show(500);
    }
    $(this).toggleClass("active").toggleClass("inactive");
  });

  $(".top-db-row").click(function() {
    window.location.href = $(this).attr("data-url");
  })
})