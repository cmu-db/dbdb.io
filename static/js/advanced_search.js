
var ordered_db_data;
var db_names = [];
var current_dbs;
var not_current_dbs = [];
var filters = [];
var LETTERS = "123456789abcdefghijklmnopqrstuvwqyz";

function get_unseen_letters() {
  var db_letter, index;
  var LETTERS = ["1", "2","3","4","5","6","7","8","9","a",
                 "b","c","d","e","f","g","h","i","j","k",
                 "l","m","n","o","p","q","r","s","t","u",
                 "v","w","q", "x", "y","z"];
  for (var i = 0; i < current_dbs.length; i++) {
    db_letter = current_dbs[i].data.name.slice(0, 1).toLowerCase();
    index = LETTERS.indexOf(db_letter);
    if (index > -1) {
      LETTERS.splice(index, 1);
    }
  }
  console.log(LETTERS);
  return LETTERS;
}

function clear_unseen_letters() {
  var letters = get_unseen_letters();
  for (var i in letters) {
    $("#letter-" + letters[i].toUpperCase()).hide();
  }
  if (letters.length == 36) {
    $(".no-results").show();
  }
}

function populate_current_dbs() {
  for (var i = 0; i < current_dbs.length; i++) {
    var id = current_dbs[i].id;
    $("#" + id).show();
  }
}

function clear_all_dbs() {
  for (var i = 0; i < db_names.length; i++) {
    var id = db_names[i].id;
    $("#" + id).hide();
  }
}

function filter_current_dbs(attribute) {
  var new_dbs = []
  filters.push(attribute);
  for (var i = 0; i < current_dbs.length; i ++) {
    if (current_dbs[i].data["support_" + attribute.toLowerCase()]) {
      new_dbs.push(current_dbs[i])
    } else {
      $("#" + current_dbs[i].id).hide();
      not_current_dbs.push(current_dbs[i])
    }
  }
  current_dbs = new_dbs;
  clear_unseen_letters();
}

function unfilter_current_dbs(attribute) {
  var new_not_current_dbs = []
  var attribute;
  var db, db_letter;
  var valid = true;
  var i = filters.indexOf(attribute);
  if (i > -1) {
    filters.splice(i, 1);
  }
  for (var i = 0; i < not_current_dbs.length; i++) {
    db = not_current_dbs[i]
    for (var j = 0; j < filters.length; j++) {
      attribute = filters[j];
      if (!(db.data["support_" + attribute.toLowerCase()])) {
        valid = false;
        break;
      }
    }
    if (valid) {
      current_dbs.push(db);
      $("#" + db.id).show();
      db_letter = db.data.name.slice(0, 1).toUpperCase();
      $("#letter-" + db_letter).show();
      $(".no-results").hide();
    } else {
      new_not_current_dbs.push(db);
      valid = true;
    }
  }
}

function load_clickers() {
  $(".search-checkbox").change(function() {
    var value = $(this).attr("value");
    if ($(this).is(":checked")) {
      console.log("in here");
      filter_current_dbs(value);
    } else {
      unfilter_current_dbs(value);
    }
  })
}

$(document).ready(function() {
  var opts = {
    lines: 13, // The number of lines to draw
    length: 20, // The length of each line
    width: 10, // The line thickness
    radius: 30, // The radius of the inner circle
    corners: 1, // Corner roundness (0..1)
    rotate: 0, // The rotation offset
    direction: 1, // 1: clockwise, -1: counterclockwise
    color: '#fff', // #rgb or #rrggbb or array of colors
    speed: 1, // Rounds per second
    trail: 60, // Afterglow percentage
    shadow: false, // Whether to render a shadow
    hwaccel: false, // Whether to use hardware acceleration
    className: 'spinner', // The CSS class to assign to the spinner
    zIndex: 2e9, // The z-index (defaults to 2000000000)
    top: '50%', // Top position relative to parent
    left: '50%' // Left position relative to parent
  };
  var target = document.getElementsByClassName("cover-up")[0];
  var spinner = new Spinner(opts).spin(target);
  $.ajax({
    type: 'GET',
    url: "/alphabetized/",
    contentType: 'application/json',
    success: function (data) {
      $(".cover-up").fadeOut();
      ordered_db_data = data;
      for (var i = 0; i < ordered_db_data.length; i++) {
        var letter_entry = ordered_db_data[i].dbs;
        for (var j = 0; j < letter_entry.length; j++) {
          db_names.push(letter_entry[j]);
        }
      }
      current_dbs = db_names
      console.log(current_dbs)
      load_clickers();
    },
    error: function(a , b, c){
      console.log('There is an error in quering for alphabetized stuff');
    },
    async: true
  });
})