
$(document).ready(function() {
  $(".revision-row").click(function() {
    window.location.href = $(this).attr("data-url");
  })

  $(".db-title").hover(function() {
    $(".back-arrow").css("color", "black");
  }, function() {
    $(".back-arrow").css("color", "white");
  });

  $(".db-title").click(function() {
    console.log($(this).attr("data-url"));
    window.location.href = $(this).attr("data-url");
  })
})