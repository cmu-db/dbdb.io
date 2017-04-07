
NEXT_SELECTOR = {
  "question-check": "green-check",
  "green-check": "grey-check",
  "grey-check": "question-check"
};

NEXT_IMAGE = {
  "question-check": "/static/images/green-check.png",
  "green-check": "/static/images/black-cross.png",
  "grey-check": "/static/images/question-check.png"
};

$(document).ready(function() {
  $(".field-selector").click(function() {
    var curr_check = $(this).attr("data-current-check");
    $(this).removeClass(curr_check);
    $(this).addClass(NEXT_SELECTOR[curr_check]);
    $(this).attr("data-current-check", NEXT_SELECTOR[curr_check]);
    $(this).attr("src", NEXT_IMAGE[curr_check])
  });
  $(".search-button").click(function() {
    var results = {};
    $(".field-selector").each(function(i) {
      var field = $(this).attr("data-field");
      var check = $(this).attr("data-current-check");
      results[field] = check;
    });
    urlReq = "/" + "advancedsearch?" + jQuery.param(results);
    document.location.href = urlReq;
  })
});