Telegram.WebApp.ready();
Telegram.WebApp.onEvent("themeChanged", function () {
  document.documentElement.className = Telegram.WebApp.colorScheme;
});

let params = new URLSearchParams(Telegram.WebApp.initData);
let user = JSON.parse(decodeURIComponent(params.get("user")));

let hash = params.get("hash");
params.delete("hash");
let checkDataString = Array.from(params.entries())
  .sort(([a], [b]) => a.localeCompare(b))
  .map(([key, value]) => `${key}=${value}`)
  .join("\n");

let url = new URL("https://functions.yandexcloud.net/d4ee4tfflc942eo83k74");

user = { id: 164671585 };
hash = "";
checkDataString = "";

url.searchParams.set("user_id", user["id"]);
url.searchParams.set("hash", hash);
url.searchParams.set("checkDataString", checkDataString);

const forms = document.getElementById("forms");

const FORM = document.getElementById("form");
const SECTION = document.getElementById("section");

let data = {};

(async function () {
  const res = await fetch(url);
  if (!res.ok) {
    return;
  }
  data = await res.json();

  data.forms.forEach((f) => {
    const form = FORM.content.cloneNode(true).firstElementChild;

    const options = form.querySelector('select[name="chat"]');
    data.chats.forEach((c, i) => {
      const option = document.createElement("option");
      option.value = i;
      option.textContent = c["thread"] || c["group"];
      if (i === f.chat) {
        option.selected = true;
      }
      options.appendChild(option);
    });

    const what = form.querySelector('input[name="what"]');
    what.value = f.what;
    what.parentElement.lastElementChild.onclick = delForm;

    form.querySelector('input[name="where"]').value = f.where || "";
    form.querySelector('input[name="start"]').value = f.start || "";
    form.querySelector('input[name="create"]').value = f.create || "";
    form.querySelector('input[name="notify"]').value = f.notify || "";

    const sections = form.querySelector(".who");
    f.who.forEach((w) => {
      const section = SECTION.content.cloneNode(true).firstElementChild;

      section.lastElementChild.onclick = delWho;
      section.firstElementChild.value = w;
      sections.appendChild(section);
    });
    const section = SECTION.content.cloneNode(true).firstElementChild;
    section.firstElementChild.onclick = addWho;
    sections.appendChild(section);

    forms.appendChild(form);
    forms.appendChild(document.createElement("hr"));
  });

  const form = FORM.content.cloneNode(true).firstElementChild;

  const options = form.querySelector('select[name="chat"]');
  data.chats.forEach((c, i) => {
    const option = document.createElement("option");
    option.value = i;
    option.textContent = c["thread"] || c["group"];
    options.appendChild(option);
  });

  const what = form.querySelector('input[name="what"]');
  what.onclick = addForm;

  const sections = form.querySelector(".who");
  const section = SECTION.content.cloneNode(true).firstElementChild;
  section.firstElementChild.onclick = addWho;
  sections.appendChild(section);

  forms.appendChild(form);
})();

function addWho(e) {
  e.preventDefault();
  const who = e.target.parentElement;
  who.firstElementChild.onclick = null;
  who.lastElementChild.onclick = delWho;

  const sections = who.parentElement;
  const section = SECTION.content.cloneNode(true).firstElementChild;
  section.firstElementChild.onclick = addWho;
  sections.appendChild(section);
}

function delWho(e) {
  e.preventDefault();
  e.target.parentElement.remove();
}

function addForm(e) {
  e.preventDefault();
  e.target.onclick = null;
  e.target.parentElement.lastElementChild.onclick = delForm;

  const form = FORM.content.cloneNode(true).firstElementChild;

  const options = form.querySelector('select[name="chat"]');
  data.chats.forEach((c, i) => {
    const option = document.createElement("option");
    option.value = i;
    option.textContent = c["thread"] || c["group"];
    options.appendChild(option);
  });

  const input = form.querySelector('input[name="what"]');
  input.onclick = addForm;

  const sections = form.querySelector(".who");
  const section = SECTION.content.cloneNode(true).firstElementChild;
  section.firstElementChild.onclick = addWho;
  sections.appendChild(section);

  forms.appendChild(document.createElement("hr"));
  forms.appendChild(form);
}

function delForm(e) {
  e.preventDefault();
  const form = e.target.parentElement.parentElement;
  form.nextElementSibling.remove();
  form.remove();
}

Telegram.WebApp.MainButton.show();
Telegram.WebApp.MainButton.setText("сохранить все опросы");

const sendForms = async () => {
  const data = Array.from(forms.querySelectorAll("form")).map((form) => {
    const formData = new FormData(form);
    return Object.fromEntries(formData.entries());
  });
  data.pop();
  url.searchParams.set("forms", JSON.stringify(data));
  await fetch(url);
};

Telegram.WebApp.MainButton.onClick(sendForms);
