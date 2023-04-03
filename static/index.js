function show_choice_chat_or_dialog(mobile=false) {
    let a_plus = get_page(mobile).querySelector('#plus');
    a_plus.style.display = "none";
    let tbl_choice = get_page(mobile).querySelector('#tbl-choice');
    tbl_choice.style.display = "table";
}

function show_form_chat(mobile=false) {
    let form = get_page(mobile).querySelector('#form-new-chat');
    form.style.display = "block";
    let tbl_choice = get_page(mobile).querySelector('#tbl-choice');
    tbl_choice.style.display = "none";
}

function show_form_dialog(mobile=false) {
    let form = get_page(mobile).querySelector('#form-new-dialog');
    form.style.display = "block";
    let tbl_choice = get_page(mobile).querySelector('#tbl-choice');
    tbl_choice.style.display = "none";
}

function show_form_join_chat(mobile=false) {
    let a =get_page(mobile).querySelector("#join_chat");
    a.style["display"] = "none";
    let frm = get_page(mobile).querySelector("#form-join-chat");
    frm.style["display"] = "block";
}


function search(mobile=false) {
    let page = get_page(mobile);
    let coll = page.getElementsByClassName("chat");
    let text = page.querySelector("#chat-search").value;

    for (let i = 0; i < coll.length; ++i) {
        let chat = coll[i];
        let a_in_chat = chat.children[0];
        if (a_in_chat.id === "join_chat" || a_in_chat.id === "plus")
            continue;

        a_in_chat.innerHTML = a_in_chat.innerHTML.replace('<span style="color:red; display: initial;">', "").replace("</span>", "");

        if (text === "") {
            chat.style["display"] = "inherit";
        } else if (a_in_chat.innerText.includes(text)) {
            chat.style["display"] = "inherit";
            a_in_chat.innerHTML = a_in_chat.innerHTML.replace(text, `<span style="color:red; display: initial;">${text}</span>`);
        } else {
            chat.style["display"] = "none";
        }
    }
}

[mobile_document, desktop_document].forEach(obj => {
    obj.querySelector('#chat-search').addEventListener(
        "keydown",
        ev => {search(obj === mobile_document)}
    )
});

search(false);
search(true);