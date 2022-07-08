function openForm() {
  document.getElementById("popupForm").style.display = "block";
}
function closeForm() {
  document.getElementById("popupForm").style.display = "none";
}

// const form = document.getElementById('popupForm');

// form.addEventListener('submit', function handleSubmit(event) {
//   event.preventDefault();
//   form.reset();
// });
if ( window.history.replaceState ) {
  window.history.replaceState( null, null, window.location.href );
}