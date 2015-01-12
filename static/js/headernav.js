

function loadSearchBar() {
  // setup submit handling
  $("#header-searchbar").submit(function (event) {
    event.preventDefault();
    var db_name = $("#header-searchbar-input").val();
    window.location.replace("http://127.0.0.1:8000/db/" + db_name);
  })
}

$(document).ready(function() {
	loadSearchBar()
})