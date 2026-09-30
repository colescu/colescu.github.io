---
layout: archive
title: "Expat Life"
permalink: /expat/
author_profile: true
---

I have been fortunate to have spent time exploring some of the major cities in the world. Here's a map of cities I've lived in for at least a month, along with the regions I've visited:

<link rel="stylesheet" href="https://unpkg.com/maplibre-gl@6.11.2/dist/maplibre-gl.css" />
<link rel="stylesheet" href="{{ '/assets/css/expat-life.css' | relative_url }}" />

<div id="expat-map" class="expat-map" role="region" aria-label="Map of cities I have lived in" data-style-url="{{ '/assets/data/expat-streets-style.json' | relative_url }}" data-countries-url="{{ '/assets/data/world-china-view.geojson' | relative_url }}" data-maritime-url="{{ '/assets/data/china-maritime-view.geojson' | relative_url }}" data-labels-url="{{ '/assets/data/world-china-labels.geojson' | relative_url }}"></div>
<script id="expat-cities-data" type="application/json">{{ site.data.expat_cities | jsonify }}</script>
<script type="module" src="{{ '/assets/js/expat-life-map.js' | relative_url }}"></script>
