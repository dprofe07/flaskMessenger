function show_choice_chat_or_dialog() {
    let a_plus = document.getElementById('plus');
    a_plus.style.display = "none";
    let tbl_choice = document.getElementById('tbl-choice')
    tbl_choice.style.display = "table";
}

function show_form_chat() {
    let form = document.getElementById('form-new-chat');
    form.style.display = "block";
    let tbl_choice = document.getElementById('tbl-choice')
    tbl_choice.style.display = "none";
}

function show_form_dialog() {
    let form = document.getElementById('form-new-dialog');
    form.style.display = "block";
    let tbl_choice = document.getElementById('tbl-choice')
    tbl_choice.style.display = "none";
}

function show_form_join_chat() {
    let a = document.getElementById("join_chat")
    a.style["display"] = "none"
    let frm = document.getElementById("form-join-chat")
    frm.style["display"] = "block"
}

async function reload_div() {
    let div = document.getElementsByClassName('need-update')[0];
    div.outerHTML = await(await fetch('{{ storage.custom_url_for('get_dialogs_div') }}')).text();
    search(null);
}
setInterval(reload_div, 10000);

function search(ev) {
        let coll = document.getElementsByClassName("chat");
        let text = document.getElementById("chat-search").value;

        for (let i = 0; i < coll.length; ++i) {
            let chat = coll[i];
            let a_in_chat = chat.children[0];
            if (a_in_chat.id === "join_chat" ||a_in_chat.id === "plus")
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

document.getElementById('chat-search').addEventListener(
    "input",
    search
)

document.getElementById('chat-search').addEventListener(
    "keydown",
    search
)
search(null);