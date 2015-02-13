

$(document).ready(function() {
  var height = window.innerHeight - $(".navbar").height() + $(".navbar").height();
  $(".search-result-row").height(height);
  
  $(".search-result").click(function() {
    window.location.href = $(this).attr("data-url");
  })
});