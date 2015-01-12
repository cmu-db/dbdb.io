

function close_text_area($elem) {
  $elem.removeClass("editing");
  var value = $elem.find(".edited-text").val();
  $elem.empty();
  $elem.text(value);
}

function open_text_area($elem) {
  $(".yesno-description.editing").each(function() {
    close_text_area($(this));
  })
  $elem.addClass("editing");
  var value = $elem.text().trim();
  $elem.empty();
  var textarea = document.createElement("textarea");
  textarea.className = "form-control edited-text";
  textarea.value = value;
  textarea.setAttribute("rows", "6");
  $elem.append(textarea);
}

function load_click_handlers() {
  $(".check-img").click(function() {
    $(this).toggleClass("green-check").toggleClass("grey-check")
    if ($(this).hasClass("green-check")) {
      open_text_area($(this).parent().next());
    } else {
      close_text_area($(this).parent().next());
    }
  });

  $(".yesno-description").click(function() {
    if ($(this).hasClass("editing")) {
    } else {
      if ($(this).prev().find(".check-img").hasClass("green-check")) {
        open_text_area($(this));
      }
    }
  });
}

$(document).ready(function() {
  load_click_handlers();
})