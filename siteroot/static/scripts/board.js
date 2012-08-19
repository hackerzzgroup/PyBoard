modbars = ["stee", "jew", "homu", "line"]
styles = ["classic", "dark"]

function highlight(id) {
    commententry = document.getElementsByName('body')[0]
    if (commententry.value.trim() != "") {
        commententry.value = commententry.value + "\n>>" + id;
    } else {
        commententry.value = commententry.value + ">>" + id;
    }
}

function expImage(event) {
    if (this.expanded) {
        this.children[0].style.opacity = 1;
        this.children[0].style.display = "block";
        this.expandedImage.parentNode.removeChild(this.expandedImage);
        this.expanded = false;
    } else {
        if (this.expandedImage) {
            this.children[0].style.opacity = 0.5;
            this.children[0].style.display = "none";
            this.appendChild(this.expandedImage);
            this.expanded = true;
        } else {
            this.oldSrc = this.children[0].src;
            this.children[0].style.opacity = 0.5;
            this.expandedImage = new Image();
            this.expandedImage.className = "elem_img expanded";
            shadow = this;
            this.expandedImage.onload = function() {
                shadow.children[0].style.display = "none";
                shadow.appendChild(shadow.expandedImage);
                shadow.expanded = true;
            };
            this.expandedImage.onabort = this.expandedImage.onerror = function() {
                this.src = "/static/img/deleted.png";
            };
            this.expandedImage.src = this._fullURL;
        }
    }
}

function getMBSwitcherFor(id) {
    a = document.createElement("a");
    a._modbar = String(id);
    a.href = "javascript:;";
    a.className = "boardlink";
    a.style.color = "rgb(213,213,213)"
    a.innerHTML = id + " ";
    a.onclick = function(e) {
        window.currentModbar = id;
        localStorage.setItem("modbarStyle", id);
        document.getElementsByClassName("modbar")[0].className = "modbar " + id;
    }
    return a;
}

function getStyleSwitcherFor(id) {
    a = document.createElement("a");
    a._style = String(id);
    a.href = "javascript:;";
    a.className = "boardlink";
    a.setAttribute("onclick", "setStyle('"+ id +"')");
    a.innerHTML = id
    return a;
}

function setStyle(id) {
    window.currentStyle = id;
    localStorage.setItem("boardViewStyle", id);
    document.getElementById("css_main").href = "/static/style/" + id + "/main.css"
    document.getElementById("css_thrd").href = "/static/style/" + id + "/thread.css"
    document.getElementById("css_form").href = "/static/style/" + id + "/form.css"
}

function initialiseExpander() {
    ar = document.getElementsByClassName("img_cont");
    for (i = 0; i < ar.length; i++) {
        ar[i].expanded = false;
        ar[i]._fullURL = ar[i].href;
        ar[i].href = "javascript:;";
        ar[i].addEventListener('click', expImage, false);
    }
}

function initialiseModbar() {
    if (window.location.search !== "?mod") {
        return;
    }
    window.currentModbar = "homu";
    c = localStorage.getItem("modbarStyle");
    if (c !== null) {
        for (v in modbars) {
            if (c == modbars[v]) {
                window.currentModbar = c;
                document.getElementsByClassName("modbar")[0].className = "modbar " + c;
            }
        }
    }
    document.getElementById("topbar_right_content").innerHTML = "modbar: " + document.getElementById("topbar_right_content").innerHTML;
    while (modbars.length > 0) {
        document.getElementById("topbar_right_content").insertBefore(getMBSwitcherFor(modbars.pop()), document.getElementById("topbar_right_content").children[0]);
    }
}

function initialisePostForm() {
    if (localStorage.getItem("posterName") === null) {
        localStorage.setItem("posterName", "");
    }
    if (localStorage.getItem("posterMail") === null) {
        localStorage.setItem("posterMail", "");
    }
    document.getElementsByClassName("b")[0].onclick = saveForm;
    name = localStorage.getItem("posterName");
    email = localStorage.getItem("posterMail");
    if (name !== null && name.length > 0) {
        document.getElementsByName("name")[0].value = name;
    }
    if (email !== null && email.length > 0) {
        document.getElementsByName("email")[0].value = email;
    }
}

function saveForm() {
    name = document.getElementsByName("name")[0].value;
    email = document.getElementsByName("email")[0].value;
    if (name !== null && name.length > 0) {
        localStorage.setItem("posterName", name);
    } else {
        localStorage.setItem("posterName", "");
    }
    if (email !== null && email.length > 0) {
        localStorage.setItem("posterMail", email);
    } else {
        localStorage.setItem("posterMail", "");
    }
}

function highlightPost() {
    if (!window.location.hash) {
        return;
    } else {
        num = window.location.hash.substr(1);
        if (document.getElementById("post_" + num).className !== "thread op") {
            document.getElementById("post_" + num).className += " highlighted";
        }
    }
    a = document.getElementsByClassName("postno");
    for (i = 0; i < a.length; i++) {
        if (Number(a[i].href.split("#")[1]) > 0) {
            a[i].onclick = function(e) {
                a = document.getElementsByClassName("thread reply highlighted");
                for (i = 0; i < a.length; i++) {
                    a[i].className = "thread reply";
                }
                e.target.parentNode.parentNode.className += " highlighted";
            }
        }
    }
}

function initialiseStyles() {
    window.currentStyle = "classic";
    c = localStorage.getItem("boardViewStyle");
    if (c !== null) {
        for (v in styles) {
            if (c == styles[v]) {
                window.currentStyle = c;
                document.getElementById("css_main").href = "/static/style/" + c + "/main.css"
                document.getElementById("css_thrd").href = "/static/style/" + c + "/thread.css"
                document.getElementById("css_form").href = "/static/style/" + c + "/form.css"
            }
        }
    }
    sp = document.createElement("span");
    sp.innerHTML = " themes: ["
    if (styles.length > 1) {
        while (styles.length > 0) {
            sp.appendChild(getStyleSwitcherFor(styles.pop()));
            if (styles.length >= 1) {
                sp.innerHTML += " / ";
            }
        }
        sp.innerHTML += "]"
        document.getElementById("topbar_right_content").appendChild(sp);
    }
}

onloadCallbacks = [initialiseExpander];
onreadyCallbacks = [initialiseStyles, initialisePostForm, initialiseModbar, highlightPost];

document.addEventListener("DOMContentLoaded", function() {
    window.onreadyFunctionsHaveRun = true;
    for (i = 0; i < onreadyCallbacks.length; i++) {
        onreadyCallbacks[i]();
    }
}, false);

window.addEventListener("load", function() {
    if (!window.onreadyFunctionsHaveRun) {
        for (i = 0; i < onreadyCallbacks.length; i++) {
            onreadyCallbacks[i]();
        }
    }
    for (i = 0; i < onloadCallbacks.length; i++) {
        onloadCallbacks[i]();
    }
}, false);