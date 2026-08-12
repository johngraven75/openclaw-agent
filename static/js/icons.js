(function () {
  "use strict";

  const icons = {
    "badge-check": '<path d="M7.5 3.5 12 2l4.5 1.5L20 7l-1 5 1 5-3.5 3.5L12 22l-4.5-1.5L4 17l1-5-1-5z"/><path d="m8.5 12 2.2 2.2 4.8-5"/>',
    blocks: '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/><path d="M17.5 14v7M14 17.5h7"/>',
    "brain-circuit": '<path d="M9.5 4.5A3 3 0 0 0 4 6v1.5A3.5 3.5 0 0 0 3 14v1a3 3 0 0 0 3 3h1"/><path d="M14.5 4.5A3 3 0 0 1 20 6v2M9 9h3V6M15 13h3v-2M9 15v4M12 12h3"/><circle cx="9" cy="9" r="1"/><circle cx="15" cy="13" r="1"/><circle cx="9" cy="19" r="1"/><circle cx="20" cy="10" r="1"/>',
    cloud: '<path d="M17.5 19H6a4 4 0 0 1-.5-7.97A6.5 6.5 0 0 1 18 9a5 5 0 0 1-.5 10Z"/>',
    "folder-code": '<path d="M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="m10 11-2 2 2 2M14 11l2 2-2 2"/>',
    image: '<rect width="18" height="18" x="3" y="3" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-3.1-3.1a2 2 0 0 0-2.8 0L6 21"/>',
    "message-square": '<path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/>',
    mic: '<path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2M12 19v3"/>',
    play: '<path d="m6 3 14 9-14 9z"/>',
    "refresh-cw": '<path d="M20 6v5h-5M4 18v-5h5"/><path d="M18.5 9A7 7 0 0 0 6 6.5L4 11M5.5 15A7 7 0 0 0 18 17.5l2-4.5"/>',
    save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2Z"/><path d="M17 21v-8H7v8M7 3v5h8"/>',
    search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    send: '<path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/>',
    settings: '<path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z"/><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0 0 15 19.4a1.7 1.7 0 0 0-1 .6 1.7 1.7 0 0 0-.4 1.1V21h-4v-.09A1.7 1.7 0 0 0 8.6 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.51-1H3v-4h.09A1.7 1.7 0 0 0 4.6 9a1.7 1.7 0 0 0-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-.6 1.7 1.7 0 0 0 .4-1.1V3h4v.09A1.7 1.7 0 0 0 15.4 4.6a1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0 0 19.4 9c.14.38.36.72.66 1 .3.25.68.4 1.06.4H21v4h-.09a1.7 1.7 0 0 0-1.51.6Z"/>',
    "terminal-square": '<rect width="18" height="18" x="3" y="3" rx="2"/><path d="m7 8 3 3-3 3M13 15h4"/>',
  };

  function createIcons() {
    document.querySelectorAll("[data-lucide]").forEach((placeholder) => {
      const name = placeholder.getAttribute("data-lucide");
      const paths = icons[name];
      if (!paths) return;
      const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
      for (const attribute of placeholder.attributes) {
        if (attribute.name !== "data-lucide") svg.setAttribute(attribute.name, attribute.value);
      }
      svg.setAttribute("viewBox", "0 0 24 24");
      svg.setAttribute("fill", "none");
      svg.setAttribute("stroke", "currentColor");
      svg.setAttribute("stroke-width", "2");
      svg.setAttribute("stroke-linecap", "round");
      svg.setAttribute("stroke-linejoin", "round");
      svg.setAttribute("aria-hidden", "true");
      svg.innerHTML = paths;
      placeholder.replaceWith(svg);
    });
  }

  window.lucide = Object.freeze({ createIcons });
}());
