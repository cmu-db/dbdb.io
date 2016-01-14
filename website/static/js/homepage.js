

$(document).ready(function() {
  $(".ranking-row").click(function() {
    window.location.href = $(this).attr("data-url");
  });

  $(".as-button").click(function() {
    window.location.href = "/advancedsearch/"
  });

  $(".top-db-row").click(function() {
    window.location.href = $(this).attr("data-url");
  })
})
