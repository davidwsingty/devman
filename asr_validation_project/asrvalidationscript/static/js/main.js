function validateForm() {
            var x = document.forms["myForm"]["srnum"].value;
            var y = document.forms["myForm"]["list_asset"].value;
            var z = document.forms["myForm"]["ib"].value;
            if (x == "") {
                alert("SR-NUMBER must be filled out");
                return false;
               }
            if (y == "") {
                alert("LIST_ASSET must be filled out");
                return false;
               }
            if (z == "") {
                alert("INSTALLED-BASE must be filled out");
                return false;
               }
            if (x != "" && y != "" && z != ""){
                document.getElementById("btns").innerHTML = "<h2>Now Processing Data...Please wait. You will be redirected to Output Page ...</h2>";
            }
        }


