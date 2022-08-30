const main = document.querySelector('main');
const footer = document.querySelector('footer');
const global_anim_time = 500;

function ToggleWebsite(state) {
    let anim_time = state? global_anim_time : global_anim_time / 2;
    [main, footer].forEach(obj => {
        obj.style.animation = (state? '' : 'dis') +
            `appear ${anim_time}ms ease-in-out forwards`;
    });
}

function TransitionTo(link) {
    ToggleWebsite(false);
    setInterval(() => {
        document.location = link;
    }, global_anim_time / 2)
}

document.addEventListener('click', event => {
    if (event.target.href == undefined) return;
    if (!event.target.classList.contains('local')) return;
    event.preventDefault();
    TransitionTo(event.target.href);
});

ToggleWebsite(true);


