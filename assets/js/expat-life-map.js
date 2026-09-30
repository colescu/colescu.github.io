import * as maplibregl from "https://unpkg.com/maplibre-gl@6.11.2/dist/maplibre-gl.mjs";

const createPinIcon = (hometown = false) => {
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 32 44");
  svg.setAttribute("aria-hidden", "true");

  const shape = document.createElementNS("http://www.w3.org/2000/svg", "path");
  shape.setAttribute("d", "M16 1C7.7 1 1 7.7 1 16c0 11 15 27 15 27s15-16 15-27C31 7.7 24.3 1 16 1Z");
  shape.setAttribute("fill", hometown ? "#e87524" : "#2980b9");
  shape.setAttribute("stroke", hometown ? "#a94c0e" : "#17618c");
  shape.setAttribute("stroke-width", "2");

  const center = document.createElementNS("http://www.w3.org/2000/svg", "circle");
  center.setAttribute("cx", "16");
  center.setAttribute("cy", "16");
  center.setAttribute("r", "5");
  center.setAttribute("fill", "#fff");
  svg.append(shape, center);
  return svg;
};

const mapElement = document.getElementById("expat-map");
const dataElement = document.getElementById("expat-cities-data");
if (mapElement && dataElement) {
  const cities = JSON.parse(dataElement.textContent);
  if (cities.length) {
    const map = new maplibregl.Map({
      container: mapElement,
      style: mapElement.dataset.styleUrl,
      center: [20, 40],
      zoom: 2,
      attributionControl: { compact: true },
      dragRotate: false,
      touchPitch: false
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-left");
    map.scrollZoom.enable();

    map.addControl({
      onAdd() {
        const key = document.createElement("div");
        key.className = "maplibregl-ctrl expat-map-key";
        key.setAttribute("role", "group");
        key.setAttribute("aria-label", "Map legend");

        const visitedRow = document.createElement("div");
        visitedRow.className = "expat-map-key-row";
        const swatch = document.createElement("span");
        swatch.className = "expat-map-key-swatch";
        swatch.setAttribute("aria-hidden", "true");
        visitedRow.append(swatch, document.createTextNode("Places visited"));

        const livedRow = document.createElement("div");
        livedRow.className = "expat-map-key-row";
        const pin = createPinIcon();
        pin.classList.add("expat-map-key-pin");
        livedRow.append(pin, document.createTextNode("Cities lived in"));

        const hometownRow = document.createElement("div");
        hometownRow.className = "expat-map-key-row";
        const hometownPin = createPinIcon(true);
        hometownPin.classList.add("expat-map-key-pin");
        hometownRow.append(hometownPin, document.createTextNode("Hometown"));

        key.append(visitedRow, livedRow, hometownRow);
        return key;
      },
      onRemove() {}
    }, "top-right");

    const bounds = new maplibregl.LngLatBounds();
    cities.forEach((place) => {
      const longitude = Number(place.longitude);
      const latitude = Number(place.latitude);
      const height = place.hometown ? 24 : Math.min(31, 20 + 1.6 * Math.sqrt(Number(place.months)));
      const pin = document.createElement("button");
      pin.type = "button";
      pin.className = "expat-marker";
      pin.style.width = `${height * 0.73}px`;
      pin.style.height = `${height}px`;
      pin.setAttribute("aria-label", place.hometown ? `${place.city}, ${place.region}, hometown` : `${place.city}, ${place.duration}`);
      pin.append(createPinIcon(Boolean(place.hometown)));

      const popup = document.createElement("div");
      const name = document.createElement("strong");
      name.textContent = place.city;
      const detail = document.createElement("div");
      detail.textContent = place.hometown ? `${place.region}, ${place.country} · Hometown` : `${place.country} · ${place.duration}`;
      popup.append(name, detail);

      new maplibregl.Marker({ element: pin, anchor: "bottom" })
        .setLngLat([longitude, latitude])
        .setPopup(new maplibregl.Popup({ offset: height }).setDOMContent(popup))
        .addTo(map);
      bounds.extend([longitude, latitude]);
    });
    map.fitBounds(bounds, { padding: 36, maxZoom: 3 });
  }
}
