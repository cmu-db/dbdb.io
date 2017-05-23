// This js file is the script for the database_edit.html template.

var CHECK_BUTTONS = '<div class="metadata-complete-btn-check"><i class="fa fa-check"></i></div><div class="metadata-complete-btn-cross"><i class="fa fa-times"></i></div>';
var TA_CHECKS = '<div class="yesno-complete-btn-check"><i class="fa fa-check"></i></div><div class="yesno-complete-btn-cross"><i class="fa fa-times"></i></div>';
var last_saved_input_property;
var last_saved_textarea_property;

// Options being added upon editing.
var option_adds = {"written_in": [], "oses": [], "support_languages": []};

// Options being removed upon editing.
var option_removes = {"written_in": [], "oses": [], "support_languages": []};

// Citations being added upon editing
var citation_adds = {};

// Citations being removed upon editing
var citation_removes = [];

/**
 * Get cookie
 */
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

/**
 * Close the text_area for an element
 */
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

// /**
//  * Open the text_area for an element.
//  */
// function open_text_area($elem) {
//   // Close other descriptions being edited.
//   $(".yesno-description.editing").each(function() {
//     close_text_area($(this));
//   });
//   $(".save-button").show(500);
//   $(".version-message-input").show(500);
//   $elem.addClass("edited");
//   $elem.addClass("editing");
//   var value = $elem.next().text().trim();
//   last_saved_textarea_property = value;
//   $elem.empty();
//   var textarea = document.createElement("textarea");
//   textarea.className = "form-control edited-text";
//   textarea.value = value;
//   textarea.setAttribute("rows", "6");
//   $elem.append(textarea);
//   $elem.append(jQuery.parseHTML(TA_CHECKS));
// }

/**
 * Close the input area for text that's being edited.
 */
function close_input_area($elem, text) {
  // Stop editing this element
  $elem.removeClass("editing");
  if (!text) {
    text = $elem.find(".edited-text").val();
  }
  $elem.empty();
  $elem.text(text);
}

/**
 * Open input area for an element
 */
function open_input_area($elem) {
  $(".metadata-data.editing.selection").each(function() {
    close_selection_area($(this));
  });
  $(".metadata-data.editing").each(function() {
    close_input_area($(this));
  });
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

/**
 * Close the selection area for a select.
 */
function close_selection_area($elem) {
  $elem.removeClass("editing");
  $elem.next().hide();
}

/**
 * Open the selection area for a select.
 */
function open_selection_area($elem) {
  $(".metadata-data.editing.selection").each(function() {
    close_selection_area($(this));
  });
  $(".metadata-data.editing").each(function() {
    close_input_area($(this));
  });
  // $elem.addClass("edited");
  $elem.addClass("editing");
  $elem.next().show();
}

/**
 * Selects an option from the list.
 */
function make_selection_option_item(name) {
  var elem = document.createElement("span");
  elem.className = "selection-item";
  var cross = document.createElement("span");
  cross.className = "fa fa-times selection-close";
  var nameNode = document.createTextNode(name);
  elem.appendChild(nameNode);
  elem.appendChild(cross);
  return elem;
}

/**
 * Put an option back into the list.
 */
function make_selection_option_menu_item(name) {
  var elem = document.createElement("option");
  elem.className = "selection-option";
  var elem_name = document.createTextNode(name);
  elem.appendChild(elem_name);
  return elem;
}

/**
 * Helper function for removing an element from a list
 */
function remove_from_list(list, elem) {
  var i = list.indexOf(elem);
  if (i < 0) return;
  list.splice(i, 1)
}

/**
 * Handlers for selecting and deselect options. Close a list of options.
 */
function load_selection_clicks() {

  $(".selection-option").on("click", function() {
    var option_name = $(this).text();
    var newSelection = make_selection_option_item(option_name);
    var type = $(this).parent().prev().attr("data-type");
    var mult = $(this).parent().prev().attr("mult");
    var existing = $(this).parent().prev().children();
    $(".save-button").show(500);
    if (!(type in option_adds)) {
      option_adds[type] = [];
    }
    if (existing.length == 0) {
      option_adds[type].push($.trim(option_name));
      $(this).parent().prev().append(newSelection);
      $(this).remove();
    } else if (mult == "True" || mult == undefined) {
      option_adds[type].push($.trim(option_name));
      $(this).parent().prev().append(newSelection);
      $(this).remove();
    }
    if (!(type in option_removes)) {
      option_removes[type] = [];
    }
    remove_from_list(option_removes[type], option_name);
  });

  // Selection close 'x' clicked on. Put it in the list.
  $(".selection-close").on("click", function() {

    // event.stopPropagation(); is causing issues with newOptions that are
    // created. The newOptions did not have the jQuery callback and couldn't
    // be reselected anymore.
    // event.stopPropagation();

    var option_name = $.trim($(this).parent().text());
    var newOption = make_selection_option_menu_item(option_name);
    var type = $(this).parent().parent().attr("data-type");
    $(".save-button").show(500);

    if (!(type in option_removes)) {
      option_removes[type] = [];
    }
    if (option_name != "") {
      option_removes[type].push($.trim(option_name));
    }
    if (option_adds[type] != undefined && option_name in option_adds[type]) {
      remove_from_list(option_adds[type], option_name);
    }
    $(this).parent().parent().next().append(newOption);
    $(this).parent().remove();
    $(this).remove();
  });

}

/**
 * Convert image to base64 to be sent in json.
 * @param imgElem
 * @returns {string} base64 of the image
 */
function getBase64Image(imgElem) {
  // imgElem must be on the same server otherwise a cross-origin error will be thrown "SECURITY_ERR: DOM Exception 18"
    var canvas = document.createElement("canvas");
    canvas.width = imgElem.width;
    canvas.height = imgElem.height;
    var ctx = canvas.getContext("2d");
    ctx.drawImage(imgElem, 0, 0);
    var dataURL = canvas.toDataURL("image/png");
    return dataURL.replace(/^data:image\/(png|jpg);base64,/, "");
}

/**
 * Load handlers for the logo, revision button, feature check image, yes-no descriptions,
 * descriptions, metadata, the save button, and citation area.
 */
function load_click_handlers() {

    var opts = {
    lines: 15 // The number of lines to draw
  , length: 13 // The length of each line
  , width: 14 // The line thickness
  , radius: 30 // The radius of the inner circle
  , scale: 1.5 // Scales overall size of the spinner
  , corners: 1 // Corner roundness (0..1)
  , color: '#000' // #rgb or #rrggbb or array of colors
  , opacity: 0 // Opacity of the lines
  , rotate: 0 // The rotation offset
  , direction: 1 // 1: clockwise, -1: counterclockwise
  , speed: 0.7 // Rounds per second
  , trail: 56 // Afterglow percentage
  , fps: 20 // Frames per second when using setTimeout() as a fallback for CSS
  , zIndex: 2e9 // The z-index (defaults to 2000000000)
  , className: 'spinner' // The CSS class to assign to the spinner
  , top: '50%' // Top position relative to parent
  , left: '50%' // Left position relative to parent
  , shadow: false // Whether to render a shadow
  , hwaccel: false // Whether to use hardware acceleration
  , position: 'absolute' // Element positioning
  };
  var target = document.getElementById('spinner');
  var spinner = new Spinner(opts).stop();

  var image;
  var imageJSON;

  $("#logoUpload").on("change", function () {
      $(".save-button").show(500);
      var readerByte = new FileReader();
      var readerPreview = new FileReader();
      readerByte.onload = function (event) {
          var arrayBuffer = this.result,
          array = new Uint8Array(arrayBuffer);
          // imageJSON = array.join('');
          imageJSON = String.fromCharCode.apply(null, array);
          console.log(imageJSON);
      };

      readerPreview.onload = function (event) {
          $("#logo").attr('src', readerPreview.result);
      };

      image = $(this).get(0).files[0];
      readerByte.readAsArrayBuffer(image);
      readerPreview.readAsDataURL(image);
      // imageJSON = getBase64Image(document.getElementById('logo'));
  });

  $(".revision-button").on("click", function() {
    window.location.href = $(this).attr("data-url");
  });

  $(".check-img").on("click", function() {
    if ($(this).hasClass("icon-maybe")) {
      $(this).removeClass("icon-maybe").addClass("icon-yes");
      $(this).attr("src", "/static/images/icon-yes.png") ;
    } else {
      $(this).toggleClass("icon-yes").toggleClass("icon-no");
      if ($(this).hasClass("icon-yes")) {
        $(this).attr("src", "/static/images/icon-yes.png");
      } else {
        $(this).attr("src", "/static/images/icon-no.png");
      }
    }
    if ($(this).hasClass("icon-yes")) {
      $(this).parent().next().attr("data-exists", "1");
      // open_text_area($(this).parent().next());
    } else {
      $(this).parent().next().attr("data-exists", "0");
      // close_text_area($(this).parent().next());
    }
  });

  $(".yesno-description").on("click", function() {
    if ($(this).hasClass("editing")) {
      if (event.target.className == "yesno-complete-btn-check" ||
          event.target.className == "fa fa-check") {
        close_text_area($(this));
      } else if (event.target.className == "yesno-complete-btn-cross" ||
                 event.target.className == "fa fa-times") {
        close_text_area($(this), last_saved_textarea_property);
      }
    }
    // else {
    //   if ($(this).hasClass("db-description")) {
    //     open_text_area($(this));
    //   } else if ($(this).prev().find(".check-img").hasClass("icon-yes")) {
    //     open_text_area($(this));
    //   }
    // }
  });

  // $(".description-description").on("click", function() {
  //   if ($(this).hasClass("editing")) {
  //     if (event.target.className == "yesno-complete-btn-check" ||
  //         event.target.className == "fa fa-check") {
  //       close_text_area($(this));
  //     } else if (event.target.className == "yesno-complete-btn-cross" ||
  //                event.target.className == "fa fa-times") {
  //       close_text_area($(this), last_saved_textarea_property);
  //     }
  //   } else {
  //     if ($(this).hasClass("db-description")) {
  //       open_text_area($(this));
  //     } else if ($(this).prev().find(".check-img").hasClass("icon-yes")) {
  //       open_text_area($(this));
  //     }
  //   }
  // });

  $(".metadata-data").on("click", function(event) {
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

  $(".header-text").on("click", function() {
    $(this).next().click();
  });

  $(".citations-area").on("click", "span.citation-cross", function() {
    $(".save-button").show(500);
    var cite_num = $(this).parent().attr("data-num");
    citation_removes.push(cite_num);
    $(this).parent().remove();
    $(this).remove();
  });

  $(".save-button").on("click", function() {
    var changed_data = {};
    var description_key;
    var exists_key;

    $edited_elems = $(".edited");
    if ($edited_elems.length < 1) {
      return;
    }

    $edited_elems.each(function() {
      if ($(this).hasClass("yesno-description")) {
        description_key = "description_" + $(this).attr("data-type");
        exists_key = "support_" + $(this).attr("data-type");
        changed_data[exists_key] = $(this).attr("data-exists");
        changed_data[description_key] = $(this).text();
      } else {
        changed_data[$(this).attr("data-type")] = $(this).text() || $(this).val();
      }
    });

    options = {"adds": option_adds, "removes": option_removes};
    citations = {"adds": citation_adds, "removes": citation_removes};
    changed_data["model_stuff"] = JSON.stringify(options);
    changed_data["citations"] = JSON.stringify(citations);
    changed_data["image"] = JSON.stringify(imageJSON);

    var url = document;

    $('body').css('opacity', .5);
    spinner.spin(target);

    $.ajax({
      type: "POST",
      url: window.location.pathname,
      data: changed_data,
      dataType: "json",
      success: function(data) {
        window.location.replace(data.redirect);
        // $('body').css('opacity', .5);
      },
      error: function(e, xhr)
      {
        console.log(e);
        $('body').css('opacity', 1);
        spinner.stop();
      }
    });
  });

  $(".add-citation-done-btn").on("click", function() {
    $(".save-button").show(500);
    var data = {};
    var cite_num = parseInt($(".num-citations").attr("data-num"));
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
    $("#year").val("");
    data["pages"] = $("#pages").val();
    $("#pages").val("");
    data["link"] = $("#link").val();
    citation_adds[cite_num + 1] = data;
    $("#link").val("");
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
        cite_div.setAttribute("data-num", cite_num + 1);
        var cite_num_text = document.createTextNode("[" + (cite_num + 1) + "] ");
        cite_div.appendChild(cite_num_text);
        var cite_text = document.createElement("a");
        cite_text.text = data.cite;
        cite_text.href = data.link;
        cite_div.appendChild(cite_text);
        var cross_background = document.createElement("span");
        cross_background.className = "citation-cross";
        var cross = document.createElement("i");
        cross.className = "fa fa-times";
        cross_background.appendChild(cross);
        cite_div.appendChild(cross_background);
        var cite_area = document.getElementsByClassName("citations-area")[0];
        cite_area.appendChild(cite_div);
      },
      error: function(x, y, z) {
        console.log("failed: " + z);
      },
      dataType: "json"
    });

  });
}

/**
 * Load up the page.
 */
$(document).ready(function() {
  load_click_handlers();
  load_selection_clicks();
});
