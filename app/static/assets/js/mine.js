$(document).ready(function() {
    // Flash Message Fade Out
  // Check if there are any flash messages
    if ($('.alert').length) {
      // Fade out the flash message after 5 seconds
      setTimeout(function() {
        $('.alert').fadeOut('slow');
      }, 3000);  // 5000ms = 5 seconds
    }


// Function to initialize Select2

    // Default Select2
    $('.select2').select2();
    
    // Select2 with Bootstrap 4 theme
    $('.select2bs4').select2({
        theme: 'bootstrap4'
    });

});