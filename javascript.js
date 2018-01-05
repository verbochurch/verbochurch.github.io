var emailList = [];

$(document).ready(function () {
    $(".search").keyup(searchGuts);
    $(".searchToggle").click(searchGuts);
    $(".searchDropdown").change(searchGuts);
    //console.log(emailList);
});

function searchGuts() {
    emailList = [];
    var searchTerm = $(".search").val();
    var listItem = $('.results tbody').children('tr');
    var searchSplit = searchTerm.replace(/ /g, "'):containsi('");

    $.extend($.expr[':'], {
        'containsi': function (elem, i, match, array) {
            return (elem.textContent || elem.innerText || '').toLowerCase().indexOf((match[3] || "").toLowerCase()) >= 0;
        }
    });

    $(".results tbody tr").each(function (idx, elt) {
        if (checkMatch(elt) && checkGender(elt) && checkBaptism(elt) && checkAge(elt) && checkMarital(elt)) {
            emailList += ($(elt).find(".email").text());
            $(this).show();
            console.log(emailList);
        } else {
            $(this).hide();
        }
    });

    var jobCount = $('.results tbody tr:visible').length;
    if (jobCount == 1) {
        $('.counter').text(jobCount + ' item');
    } else {
        $('.counter').text(jobCount + ' items');
    }

    if (jobCount == '0') {
        $('.no-result').show();
    }
    else {
        $('.no-result').hide();
    }

    function checkMatch(elt) {
        rtn = null;
        rtn = $(":containsi('" + searchSplit + "')", elt).length > 0;
        console.log("CheckMatch", rtn);
        return rtn;
    }

    function checkGender(elt) {
        rtn = null;
        // console.log("genderButton", $('.gender').checked());
        if ($('.gender').prop("checked")) {
            console.log($('#gender').val(), $(elt).find(".genderData").text())
            rtn = ($('#gender').val() == $(elt).find(".genderData").text())
        }
        else {
            rtn = true
        }
        return rtn;
    }

    function checkBaptism(elt) {
        rtn = null;
        if ($('.baptism').prop("checked")) {
            rtn = ($('#baptism').val() == $(elt).find(".baptismData").text())
        }
        else {
            rtn = true
        }
        return rtn
    }

    function checkMarital(elt) {
        rtn = null;
        if ($('.maritalCheckbox').prop("checked")) {
            rtn = ($('#marital').val() == $(elt).find(".maritalData").text())
        }
        else {
            rtn = true
        }
        return rtn
    }

    function checkAge(elt) {
        rtn = null;
        if ($('.ageCheckbox').prop("checked")) {
            rtn = ageInRange(($('#age').val()), $(elt).find(".ageData").text())
        }
        else {
            rtn = true
        }
        return rtn
    }

    function ageInRange(ageLabel, userAge) {
        if (ageLabel == "children" && userAge <= 5) {
            return true
        }
        else if (ageLabel == "youth" && userAge <= 12 && userAge > 5) {
            return true
        }
        else if (ageLabel == "teen" && userAge <= 19 && userAge > 12) {
            return true
        }
        else if (ageLabel == "youngAdult" && userAge <= 25 && userAge > 19) {
            return true
        }
        else if (ageLabel == "adult" && userAge <= 64 && userAge > 25) {
            return true
        }
        else if (ageLabel == "senior" && userAge >= 65) {
            return true
        }
        else {
            return false
        }
    }
}

$('#confirmModal').on('show.bs.modal', function (event) {
    var button = $(event.relatedTarget); // Button that triggered the modal
    var url = button.data('url'); // Extract info from data-* attributes
    var firstname = button.data('firstname');
    var lastname = button.data('lastname');
    // If necessary, you could initiate an AJAX request here (and then do the updating in a callback).
    // Update the modal's content. We'll use jQuery here, but you could use a data binding library or other methods instead.
    var modal = $(this);
    modal.find('.modal-body').text('Are you sure you want to remove ' + firstname + ' ' + lastname + '?');
    modal.find('#modal-confirm').attr("href", url)
});



