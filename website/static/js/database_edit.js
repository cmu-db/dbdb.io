// This js file is the script for the database_edit.html template.


/**
 * Load up the page.
 */
$(document).ready(function() {

  // Citations being added upon editing
  var citation_adds = {};

  // Citations being removed upon editing
  var citation_removes = [];

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

  $(".revision-button").on("click", function() {
    window.location.href = $(this).attr("data-url");
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

    // $('body').css('opacity', .5);
    // spinner.spin(target);
    //
    // $.ajax({
    //   type: "POST",
    //   url: window.location.pathname,
    //   data: changed_data,
    //   dataType: "json",
    //   success: function(data) {
    //     window.location.replace(data.redirect);
    //     // $('body').css('opacity', .5);
    //   },
    //   error: function(e, xhr)
    //   {
    //     console.log(e);
    //     $('body').css('opacity', 1);
    //     spinner.stop();
    //   }
    // });
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
});
