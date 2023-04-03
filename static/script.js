let mobile_document = document.getElementsByClassName('mobile')[0];
let desktop_document = document.getElementsByClassName('desktop')[0];

function get_page(mobile=false) {
    return (mobile ? mobile_document : desktop_document);
}

const main_desktop = desktop_document.querySelector('main');
const main_mobile = mobile_document.querySelector('main');
const footer_desktop = desktop_document.querySelector('footer');
const footer_mobile = mobile_document.querySelector('footer');

const global_anim_time = 500;

function ToggleWebsite(state) {
    let anim_time = state? global_anim_time : global_anim_time / 2;
    [main_desktop, main_mobile, footer_desktop, footer_mobile].forEach(obj => {
        obj.style.animation = (state? '' : 'dis') +
            `appear ${anim_time}ms ease-in-out forwards`;
    });
}

function TransitionTo(link) {
    ToggleWebsite(false);
    setTimeout(() => {
        document.location = link;
    }, global_anim_time / 2)
}

document.addEventListener('click', event => {
    if (event.target.href === undefined) return;
    if (!event.target.classList.contains('local')) return;
    event.preventDefault();
    TransitionTo(event.target.href);
});

ToggleWebsite(true);


