$(document).ready(function () {
    $('#checkbox1').change(function () {
        if (!this.checked) $('.content').fadeOut('slow');
        else $('.content').fadeIn('slow');
    });
});