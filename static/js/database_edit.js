
var CHECK_BUTTONS = '<div class="metadata-complete-btn-check"><i class="fa fa-check"></i></div><div class="metadata-complete-btn-cross"><i class="fa fa-times"></i></div>'
var TA_CHECKS = '<div class="yesno-complete-btn-check"><i class="fa fa-check"></i></div><div class="yesno-complete-btn-cross"><i class="fa fa-times"></i></div>'
var last_saved_input_property;
var last_saved_textarea_property;

function close_text_area($elem, text) {
  $(".save-button").show(500);
  $elem.removeClass("editing");
  $elem.addClass("edited");
  if (!text) {
    text = $elem.find(".edited-text").val();
  }
  $elem.empty();
  $elem.text(text);
}

function open_text_area($elem) {
  $(".yesno-description.editing").each(function() {
    close_text_area($(this));
  })
  $(".save-button").show(500);
  $elem.addClass("edited");
  $elem.addClass("editing");
  var value = $elem.text().trim();
  last_saved_textarea_property = value;
  $elem.empty();
  var textarea = document.createElement("textarea");
  textarea.className = "form-control edited-text";
  textarea.value = value;
  textarea.setAttribute("rows", "6");
  $elem.append(textarea);
  $elem.append(jQuery.parseHTML(TA_CHECKS));
}

function close_input_area($elem, text) {
  $elem.removeClass("editing");
  if (!text) {
    text = $elem.find(".edited-text").val();
  }
  $elem.empty()
  $elem.text(text);
}

function open_input_area($elem) {
  $(".metadata-data.editing.selection").each(function() {
    close_selection_area($(this));
  });
  $(".metadata-data.editing").each(function() {
    close_input_area($(this));
  })
  $(".save-button").show(500);
  $elem.addClass("edited");
  $elem.addClass("editing");
  var value = $elem.text().trim();
  last_saved_input_property = value;
  $elem.empty();
  var inputbox = document.createElement("input");
  inputbox.className = "form-control edited-text";
  inputbox.value = value;
  $elem.append(inputbox);
  $elem.append(jQuery.parseHTML(CHECK_BUTTONS));
}

function close_selection_area($elem) {
  $elem.removeClass("editing");
  $elem.next().hide();
}

function open_selection_area($elem) {
  $(".metadata-data.editing.selection").each(function() {
    close_selection_area($(this));
  });
  $(".metadata-data.editing").each(function() {
    close_input_area($(this));
  })
  $elem.addClass("edited");
  $elem.addClass("editing");
  $elem.next().show();
}

function load_click_handlers() {
  $(".check-img").click(function() {
    $(this).toggleClass("green-check").toggleClass("grey-check")
    if ($(this).hasClass("green-check")) {
      $(this).parent().next().attr("data-exists", "1");
      open_text_area($(this).parent().next());
    } else {
      $(this).parent().next().attr("data-exists", "0");
      close_text_area($(this).parent().next());
    }
  });

  $(".yesno-description").click(function() {
    if ($(this).hasClass("editing")) {
      if (event.target.className == "yesno-complete-btn-check" ||
          event.target.className == "fa fa-check") {
        close_text_area($(this));
      } else if (event.target.className == "yesno-complete-btn-cross" ||
                 event.target.className == "fa fa-times") {
        close_text_area($(this), last_saved_textarea_property);
      }
    } else {
      if ($(this).hasClass("db-description")) {
        open_text_area($(this));
      } else if ($(this).prev().find(".check-img").hasClass("green-check")) {
        open_text_area($(this));
      }
    }
  });

  $(".description-description").click(function() {
    if ($(this).hasClass("editing")) {
      if (event.target.className == "yesno-complete-btn-check" ||
          event.target.className == "fa fa-check") {
        close_text_area($(this));
      } else if (event.target.className == "yesno-complete-btn-cross" ||
                 event.target.className == "fa fa-times") {
        close_text_area($(this), last_saved_textarea_property);
      }
    } else {
      if ($(this).hasClass("db-description")) {
        open_text_area($(this));
      } else if ($(this).prev().find(".check-img").hasClass("green-check")) {
        open_text_area($(this));
      }
    }
  });

  $(".metadata-data").click(function(event) {
    if ($(this).hasClass("selection")) {
      open_selection_area($(this));
    }
    if (event.target.className == "metadata-complete-btn-check" ||
        event.target.className == "fa fa-check") {
      close_input_area($(this));
    } else if (event.target.className == "metadata-complete-btn-cross" ||
               event.target.className == "fa fa-times") {
      close_input_area($(this), last_saved_input_property);
    } else {
      if ($(this).hasClass("editing")) {
      } else {
        open_input_area($(this));
      }
    }
  });

  $(".header-text").click(function(event) {
    $(this).next().click();
  })

  $(".save-button").click(function() {
    var changed_data = {},
        description_key,
        exists_key;

    $edited_elems = $(".edited");
    if ($edited_elems.length < 1) {
      return;
    }

    $edited_elems.each(function() {
      if ($(this).hasClass("yesno-description")) {
        description_key = "description_" + $(this).attr("data-type") 
        exists_key = "support_" + $(this).attr("data-type");

        changed_data[exists_key] = $(this).attr("data-exists");
        changed_data[description_key] = $(this).text();
      } else {
        changed_data[$(this).attr("data-type")] = $(this).text();
      }
    });

    console.log(changed_data);

    var url = document

    $.ajax({
      type: "POST",
      url: window.location.pathname,
      data: changed_data,
      success: function() {
      },
      dataType: "json"
    });
  })
}

$(document).ready(function() {
  load_click_handlers();
})