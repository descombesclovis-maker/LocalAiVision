import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet.markercluster/dist/MarkerCluster.css";

// leaflet.markercluster's UMD bundle reads the global `L`; expose it before that module evaluates.
(window as unknown as { L: typeof L }).L = L;

export default L;
