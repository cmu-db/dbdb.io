
var CHECK_BUTTONS = '<div class="metadata-complete-btn-check"><i class="fa fa-check"></i></div><div class="metadata-complete-btn-cross"><i class="fa fa-times"></i></div>'
var TA_CHECKS = '<div class="yesno-complete-btn-check"><i class="fa fa-check"></i></div><div class="yesno-complete-btn-cross"><i class="fa fa-times"></i></div>'
var last_saved_input_property;
var last_saved_textarea_property;
var option_states = {"written_in": [], "oses": [], "support_languages": []};
var option_adds = {"written_in": [], "oses": [], "support_languages": []};
var option_removes = {"written_in": [], "oses": [], "support_languages": []};

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

function close_text_area($elem, text) {
  $(".save-button").show(500);
  $elem.removeClass("editing");
  $elem.addClass("edited");
  if (!text) {
    text = $elem.find(".edited-text").val();
  }
  $elem.empty();
  $elem.text(text);
  $elem.next().text(text);
}

function open_text_area($elem) {
  $(".yesno-description.editing").each(function() {
    close_text_area($(this));
  })
  $(".save-button").show(500);
  $(".version-message-input").show(500);
  $elem.addClass("edited");
  $elem.addClass("editing");
  var value = $elem.next().text().trim();
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
  // $elem.addClass("edited");
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
  // $elem.addClass("edited");
  $elem.addClass("editing");
  $elem.next().show();
}

function make_selection_option_item(name) {
  var elem = document.createElement("span");
  elem.className = "selection-item"
  var cross = document.createElement("span");
  cross.className = "fa fa-times selection-close";
  var nameNode = document.createTextNode(name);
  elem.appendChild(nameNode);
  elem.appendChild(cross)
  return elem;
}

function make_selection_option_menu_item(name) {
  var elem = document.createElement("option");
  elem.className = "selection-option";
  var elem_name = document.createTextNode(name);
  elem.appendChild(elem_name);
  return elem;
}

function remove_from_list(list, elem) {
  var i = list.indexOf(elem);
  if (i < 0) return;
  list.splice(i, 1)
}

function load_selection_clicks() {
  $(".selection-option").click(function() {
    var option_name = $(this).text();
    var newOption = make_selection_option_item(option_name);
    var type = $(this).parent().prev().attr("data-type");
    var mult = $(this).parent().prev().attr("mult");
    var existing = $(this).parent().prev().children();
    $(".save-button").show(500);
    if (!(type in option_adds)) {
      option_adds[type] = [];
    }
    if (existing.length == 0) {
      option_adds[type].push($.trim(option_name));
      $(this).parent().prev().append(newOption);
      $(this).remove();
    } else if (mult == "True" || mult == undefined) {
      option_adds[type].push($.trim(option_name));
      $(this).parent().prev().append(newOption);
      $(this).remove();
    }
    if (!(type in option_removes)) {
      option_removes[type] = [];
    }
    remove_from_list(option_removes[type], option_name);
  });

  $(".selection-close").click(function(event) {
    event.stopPropagation();
    var option_name = $.trim($(this).parent().text());
    var newOption = make_selection_option_menu_item(option_name);
    var type = $(this).parent().parent().attr("data-type");
    if (!(type in option_removes)) {
      option_removes[type] = [];
    }
    option_removes[type].push($.trim(option_name));
    if (option_adds[type] != undefined && option_name in option_adds[type]) {
      remove_from_list(option_adds[type], option_name);
    }
    $(this).parent().parent().next().append(newOption);
    $(this).parent().remove();
    $(this).remove();
  })
}

function load_click_handlers() {

  $(".revision-button").click(function() {
    window.location.href = $(this).attr("data-url");
  });

  $(".check-img").click(function() {
    if ($(this).hasClass("question-check")) {
      $(this).removeClass("question-check").addClass("green-check")
    } else {
      $(this).toggleClass("green-check").toggleClass("grey-check")
    }
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
    if (event.target.className == "fa fa-times selection-close") {
      load_selection_clicks();
    } else if (event.target.className == "metadata-complete-btn-check" ||
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
  load_selection_clicks();

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
        changed_data[$(this).attr("data-type")] = $(this).text() || $(this).val();
      }
    });

    options = {"adds": option_adds, "removes": option_removes}
    changed_data["model_stuff"] = JSON.stringify(options);
    var url = document
    $.ajax({
      type: "POST",
      url: window.location.pathname,
      data: changed_data,
      dataType: "json",
      success: function(data) {
        window.location.replace(data.redirect);
      },
      error: function(e, xhr)
      {
        console.log(e);
      }
    });
  })

  $(".add-citation-done-btn").click(function() {
    var data = {}
    var cite_num = parseInt($(".num-citations").attr("data-num"))
    var db_name = $(".db-name").attr("data-name");
    data["number"] = cite_num + 1;
    data["db_name"] = db_name;
    data["authors"] = $("#authors").val();
    $("#authors").val("");
    data["title"] = $("#title").val();
    $("#title").val("");
    data["journal"] = $("#journal").val();
    $("#journal").val("");
    data["volume"] = $("#volume").val();
    $("#volume").val("");
    data["year"] = $("#year").val();
    $("#year").val("")
    data["pages"] = $("#pages").val();
    $("#pages").val("");
    data["download"] = $("#download-url").val();
    $("#download-url").val("");
    var csrftoken = getCookie('csrftoken');
    $.ajax({
      type: "POST",
      url: "/addpublication/",
      data: data,
      beforeSend: function (xhr) {
        xhr.withCredentials = true;
        xhr.setRequestHeader("X-CSRFToken", csrftoken);
      },
      success: function(data) {
        $(".num-citations").attr("data-num", cite_num + 1);
        var cite_div = document.createElement("div");
        cite_div.className = "citation";
        var cite_text = document.createTextNode("[" + (cite_num + 1) + "] " + data.cite);
        cite_div.appendChild(cite_text);
        var cite_area = document.getElementsByClassName("citations-area")[0];
        cite_area.appendChild(cite_div);
      },
      error: function(x, y, z) {
        console.log("failed: " + z);
      },
      dataType: "json"
    })
  })
}

function load_page_data() {
  $(".written_in-section").each(function() {
    option_states["written_in"].push($.trim($(this).text()));
  });
  $(".oses-section").each(function() {
    option_states["oses"].push($.trim($(this).text()));
  });
  $(".support_languages-section").each(function() {
    option_states["support_languages"].push($.trim($(this).text()));
  });
}

$(document).ready(function() {
  load_page_data();
  load_click_handlers();
})
